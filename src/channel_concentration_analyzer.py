"""
Channel Concentration Analyzer.

Computes outlet- and channel-level concentration metrics for pharmacy
distribution portfolios, including:

* Herfindahl-Hirschman Index (HHI) across outlets — 0-10,000 scale
* Normalised HHI (HHI*) — scale-free 0-1 score
* Effective-number-of-outlets (1 / HHI_fraction)
* Pareto 80-20 ranking — how few outlets drive 80% of revenue
* Retail-vs-hospital channel split with concentration per channel

The module is intentionally domain-honest: it works with real revenue
aggregations from transactional data, handles zero-sales outlets,
missing channel labels, duplicate outlet_ids, NaN values, and empty
DataFrames without silently dropping them.

References
----------
* Rhoades, S. A. (1993). *The Herfindahl-Hirschman Index*.
  Federal Reserve Bulletin, 79, 188-189.
* US DOJ/FTC Horizontal Merger Guidelines (HHI thresholds).
* Pareto, V. (1896). *Cours d'Economie Politique*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# Concentration band thresholds mirror the US DOJ/FTC Horizontal Merger
# Guidelines: 0-1,500 unconcentrated, 1,500-2,500 moderate, 2,500+ high.
HHI_UNCONCENTRATED = 1500
HHI_MODERATE = 2500

DEFAULT_PARETO_CUTOFF = 0.80
MISSING_CHANNEL_LABEL = "Unknown"


@dataclass(frozen=True)
class ConcentrationResult:
    """Immutable container for portfolio concentration metrics.

    Attributes:
        hhi: Herfindahl-Hirschman Index on the 0-10,000 scale where
            10,000 represents a pure monopoly across outlets.
        hhi_normalised: Scale-free HHI in [0, 1]. Accounts for the number
            of outlets so portfolios of different sizes are comparable.
        effective_outlets: Inverse of the HHI fraction — roughly the
            number of "equally sized" outlets that would yield the same
            concentration.
        band: Qualitative label derived from HHI thresholds
            ('unconcentrated', 'moderate', 'high').
        outlet_count: Number of outlets that contributed non-zero revenue.
        zero_sales_outlets: Number of outlets whose revenue summed to
            zero and were therefore excluded from HHI.
        top_outlet_share: Revenue share of the single largest outlet.
    """

    hhi: float
    hhi_normalised: float
    effective_outlets: float
    band: str
    outlet_count: int
    zero_sales_outlets: int
    top_outlet_share: float


@dataclass(frozen=True)
class ParetoResult:
    """Immutable Pareto 80-20 ranking output.

    Attributes:
        cutoff: Cumulative revenue-share cutoff used (default 0.80).
        outlets_to_cutoff: Count of ranked outlets needed to reach
            ``cutoff`` of total revenue.
        share_of_outlets: ``outlets_to_cutoff`` as a fraction of the
            total non-zero outlet count.
        ranking: DataFrame sorted by revenue descending with columns
            ``outlet_id``, ``revenue``, ``revenue_share``,
            ``cumulative_share``, ``rank``, and ``within_cutoff`` (bool).
    """

    cutoff: float
    outlets_to_cutoff: int
    share_of_outlets: float
    ranking: pd.DataFrame = field(repr=False)


@dataclass(frozen=True)
class ChannelSplitResult:
    """Retail-vs-hospital (or any-channel) split with concentration.

    Attributes:
        per_channel: DataFrame indexed by ``channel_type`` with columns
            ``revenue``, ``units_sold``, ``outlet_count``,
            ``revenue_share``, and ``hhi_within_channel``.
        dominant_channel: Channel with the highest revenue share.
        dominant_share: Revenue share of the dominant channel in [0, 1].
    """

    per_channel: pd.DataFrame = field(repr=False)
    dominant_channel: str
    dominant_share: float


class ChannelConcentrationAnalyzer:
    """Concentration and Pareto analytics for pharmacy distribution.

    The analyzer is stateless — each public method takes a DataFrame
    and returns a new immutable result object. Input DataFrames are
    never mutated.

    Example:
        >>> analyzer = ChannelConcentrationAnalyzer()
        >>> df = pd.DataFrame({
        ...     "outlet_id": ["A", "B", "C", "D"],
        ...     "channel_type": ["retail", "retail", "hospital", "hospital"],
        ...     "revenue": [4000, 3000, 2000, 1000],
        ... })
        >>> result = analyzer.compute_hhi(df)
        >>> round(result.hhi, 0)
        3000.0
    """

    def __init__(
        self,
        outlet_col: str = "outlet_id",
        channel_col: str = "channel_type",
        revenue_col: str = "revenue",
        units_col: str = "units_sold",
    ) -> None:
        """Initialise the analyzer with the column names in the caller's schema.

        Args:
            outlet_col: Column holding the unique outlet identifier.
            channel_col: Column holding the channel label
                (e.g. ``retail``, ``hospital``, ``institutional``).
            revenue_col: Column holding the per-row revenue number.
            units_col: Column holding per-row units sold.
        """
        self.outlet_col = outlet_col
        self.channel_col = channel_col
        self.revenue_col = revenue_col
        self.units_col = units_col

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _require_df(self, df: pd.DataFrame) -> None:
        """Validate the DataFrame is non-empty and a DataFrame.

        Raises:
            TypeError: If ``df`` is not a :class:`pandas.DataFrame`.
            ValueError: If ``df`` is empty.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Expected a pandas DataFrame")
        if df.empty:
            raise ValueError("Input DataFrame is empty")

    def _require_column(self, df: pd.DataFrame, column: str) -> None:
        """Ensure ``column`` exists in ``df``.

        Raises:
            ValueError: If ``column`` is absent.
        """
        if column not in df.columns:
            raise ValueError(f"Required column '{column}' not found")

    def _aggregate_outlet_revenue(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a new DataFrame with one row per outlet and summed revenue.

        Handles NaN revenue by coercing to 0 and collapses duplicate
        ``outlet_id`` rows via summation. The input DataFrame is not
        mutated.
        """
        self._require_column(df, self.outlet_col)
        self._require_column(df, self.revenue_col)

        working = df[[self.outlet_col, self.revenue_col]].copy()
        working[self.revenue_col] = pd.to_numeric(
            working[self.revenue_col], errors="coerce"
        ).fillna(0.0)
        working = working.dropna(subset=[self.outlet_col])
        grouped = (
            working.groupby(self.outlet_col, as_index=False)[self.revenue_col]
            .sum()
            .rename(columns={self.revenue_col: "revenue"})
        )
        return grouped

    # ------------------------------------------------------------------
    # HHI / concentration
    # ------------------------------------------------------------------
    def compute_hhi(self, df: pd.DataFrame) -> ConcentrationResult:
        """Compute outlet-level HHI across the portfolio.

        The HHI is the sum of squared market shares expressed in
        percentage points. Zero-sales outlets are excluded from the
        HHI calculation but counted separately so callers can surface
        data-quality issues.

        Args:
            df: DataFrame with at least outlet and revenue columns. NaN
                revenues are treated as zero. Duplicate outlet rows are
                summed.

        Returns:
            A :class:`ConcentrationResult` describing the concentration
            of the portfolio.

        Raises:
            TypeError: If ``df`` is not a DataFrame.
            ValueError: If ``df`` is empty or required columns are missing.
        """
        self._require_df(df)
        grouped = self._aggregate_outlet_revenue(df)

        total_revenue = float(grouped["revenue"].sum())
        non_zero = grouped[grouped["revenue"] > 0].copy()
        zero_sales_outlets = int(len(grouped) - len(non_zero))

        if total_revenue <= 0 or non_zero.empty:
            return ConcentrationResult(
                hhi=0.0,
                hhi_normalised=0.0,
                effective_outlets=0.0,
                band="undefined",
                outlet_count=0,
                zero_sales_outlets=zero_sales_outlets,
                top_outlet_share=0.0,
            )

        shares_fraction = non_zero["revenue"].to_numpy() / total_revenue
        hhi_fraction = float(np.sum(shares_fraction ** 2))
        hhi_percent = hhi_fraction * 10_000

        n = len(non_zero)
        if n > 1:
            hhi_normalised = (hhi_fraction - 1 / n) / (1 - 1 / n)
        else:
            hhi_normalised = 1.0

        effective_outlets = 1 / hhi_fraction if hhi_fraction > 0 else 0.0
        top_outlet_share = float(shares_fraction.max())

        return ConcentrationResult(
            hhi=round(hhi_percent, 2),
            hhi_normalised=round(float(hhi_normalised), 4),
            effective_outlets=round(effective_outlets, 2),
            band=self._band(hhi_percent),
            outlet_count=n,
            zero_sales_outlets=zero_sales_outlets,
            top_outlet_share=round(top_outlet_share, 4),
        )

    def _band(self, hhi: float) -> str:
        """Classify an HHI value using DOJ/FTC thresholds."""
        if hhi < HHI_UNCONCENTRATED:
            return "unconcentrated"
        if hhi < HHI_MODERATE:
            return "moderate"
        return "high"

    # ------------------------------------------------------------------
    # Pareto / 80-20
    # ------------------------------------------------------------------
    def pareto_ranking(
        self,
        df: pd.DataFrame,
        cutoff: float = DEFAULT_PARETO_CUTOFF,
    ) -> ParetoResult:
        """Rank outlets by revenue and report the Pareto cutoff.

        Args:
            df: DataFrame containing outlet and revenue columns.
            cutoff: Cumulative-share threshold in the open interval
                ``(0, 1]``. Defaults to 0.80 for the classic 80/20 rule.

        Returns:
            A :class:`ParetoResult` with the full ranking and the
            number of outlets required to reach ``cutoff`` of revenue.

        Raises:
            TypeError: If ``df`` is not a DataFrame.
            ValueError: If ``df`` is empty, required columns missing,
                or ``cutoff`` is outside ``(0, 1]``.
        """
        if not 0 < cutoff <= 1:
            raise ValueError("cutoff must be in the interval (0, 1]")
        self._require_df(df)
        grouped = self._aggregate_outlet_revenue(df)
        non_zero = grouped[grouped["revenue"] > 0].copy()

        if non_zero.empty:
            empty_ranking = pd.DataFrame(
                columns=[
                    self.outlet_col,
                    "revenue",
                    "revenue_share",
                    "cumulative_share",
                    "rank",
                    "within_cutoff",
                ]
            )
            return ParetoResult(
                cutoff=cutoff,
                outlets_to_cutoff=0,
                share_of_outlets=0.0,
                ranking=empty_ranking,
            )

        ranked = non_zero.sort_values("revenue", ascending=False).reset_index(
            drop=True
        )
        total_revenue = float(ranked["revenue"].sum())
        ranked["revenue_share"] = ranked["revenue"] / total_revenue
        ranked["cumulative_share"] = ranked["revenue_share"].cumsum()
        ranked["rank"] = np.arange(1, len(ranked) + 1)

        # outlets_to_cutoff: smallest k such that cumulative_share[k-1] >= cutoff
        at_or_above = ranked.index[ranked["cumulative_share"] >= cutoff]
        if len(at_or_above) == 0:
            outlets_to_cutoff = len(ranked)
        else:
            outlets_to_cutoff = int(at_or_above[0]) + 1

        ranked["within_cutoff"] = ranked["rank"] <= outlets_to_cutoff
        share_of_outlets = outlets_to_cutoff / len(ranked)

        return ParetoResult(
            cutoff=cutoff,
            outlets_to_cutoff=outlets_to_cutoff,
            share_of_outlets=round(share_of_outlets, 4),
            ranking=ranked,
        )

    # ------------------------------------------------------------------
    # Channel split (retail vs hospital vs ...)
    # ------------------------------------------------------------------
    def channel_split(self, df: pd.DataFrame) -> ChannelSplitResult:
        """Break revenue down by channel and compute within-channel HHI.

        Missing or blank ``channel_type`` values are normalised to
        ``'Unknown'`` instead of being dropped, so data-quality issues
        remain visible in the output.

        Args:
            df: DataFrame with outlet, channel, revenue, and optionally
                units-sold columns.

        Returns:
            A :class:`ChannelSplitResult` with per-channel totals and
            the dominant channel.

        Raises:
            TypeError: If ``df`` is not a DataFrame.
            ValueError: If ``df`` is empty or required columns missing.
        """
        self._require_df(df)
        self._require_column(df, self.outlet_col)
        self._require_column(df, self.channel_col)
        self._require_column(df, self.revenue_col)

        working = df.copy()
        working[self.revenue_col] = pd.to_numeric(
            working[self.revenue_col], errors="coerce"
        ).fillna(0.0)
        working[self.channel_col] = (
            working[self.channel_col]
            .fillna(MISSING_CHANNEL_LABEL)
            .astype(str)
            .str.strip()
            .replace({"": MISSING_CHANNEL_LABEL})
        )

        if self.units_col in working.columns:
            working[self.units_col] = pd.to_numeric(
                working[self.units_col], errors="coerce"
            ).fillna(0.0)
        else:
            working[self.units_col] = 0.0

        # Aggregate per outlet within each channel so HHI is outlet-level.
        per_outlet = (
            working.groupby([self.channel_col, self.outlet_col], as_index=False)
            .agg({self.revenue_col: "sum", self.units_col: "sum"})
        )

        records: List[Dict[str, float]] = []
        for channel, group in per_outlet.groupby(self.channel_col):
            channel_revenue = float(group[self.revenue_col].sum())
            channel_units = float(group[self.units_col].sum())
            positive = group[group[self.revenue_col] > 0]
            if channel_revenue > 0 and not positive.empty:
                shares = positive[self.revenue_col].to_numpy() / channel_revenue
                channel_hhi = float(np.sum(shares ** 2) * 10_000)
            else:
                channel_hhi = 0.0
            records.append(
                {
                    self.channel_col: channel,
                    "revenue": round(channel_revenue, 2),
                    "units_sold": round(channel_units, 2),
                    "outlet_count": int(group[self.outlet_col].nunique()),
                    "hhi_within_channel": round(channel_hhi, 2),
                }
            )

        summary = pd.DataFrame(records)
        total_revenue = float(summary["revenue"].sum())
        if total_revenue > 0:
            summary["revenue_share"] = (summary["revenue"] / total_revenue).round(
                4
            )
        else:
            summary["revenue_share"] = 0.0

        summary = summary.sort_values("revenue", ascending=False).reset_index(
            drop=True
        )
        dominant_row = summary.iloc[0]
        return ChannelSplitResult(
            per_channel=summary,
            dominant_channel=str(dominant_row[self.channel_col]),
            dominant_share=float(dominant_row["revenue_share"]),
        )

    # ------------------------------------------------------------------
    # Convenience summary
    # ------------------------------------------------------------------
    def summary(
        self,
        df: pd.DataFrame,
        cutoff: float = DEFAULT_PARETO_CUTOFF,
    ) -> Dict[str, object]:
        """Compute all concentration metrics in a single call.

        Args:
            df: Portfolio DataFrame.
            cutoff: Pareto cutoff passed to :meth:`pareto_ranking`.

        Returns:
            A dict with the HHI concentration result, Pareto ranking,
            and channel split. Useful for CLI dashboards or JSON export.
        """
        return {
            "concentration": self.compute_hhi(df),
            "pareto": self.pareto_ranking(df, cutoff=cutoff),
            "channel_split": self.channel_split(df),
        }
