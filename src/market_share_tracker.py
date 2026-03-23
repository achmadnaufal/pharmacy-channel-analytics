"""
Market Share Tracker for Pharmacy Channel Analytics.

Tracks drug-level and brand-level market share across pharmacy channels
(Hospital, Retail, Specialty) over time. Computes absolute share,
share of voice, trend direction, and competitive dynamics.

Author: github.com/achmadnaufal
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class MarketShareTracker:
    """
    Tracks and analyses market share evolution across brands and channels.

    Market share is computed as a brand's volume (units or value) as a
    percentage of total market volume in that channel and period.

    Attributes:
        market_name (str): Name of the market or therapeutic area.
        records (list[dict]): Raw sales records.

    Example::

        tracker = MarketShareTracker(market_name="Antidiabetic - Oral")
        tracker.record_sales("Metformin", "Retail", "2025-Q1", units=15200, value_usd=18240)
        tracker.record_sales("Sitagliptin", "Retail", "2025-Q1", units=8400, value_usd=84000)
        tracker.record_sales("Metformin", "Retail", "2025-Q2", units=16100, value_usd=19320)
        tracker.record_sales("Sitagliptin", "Retail", "2025-Q2", units=8800, value_usd=88000)

        print(tracker.market_share_by_period("Retail"))
        print(tracker.share_trend("Metformin", "Retail"))
    """

    def __init__(self, market_name: str = "Pharma Market") -> None:
        """
        Initialize the MarketShareTracker.

        Args:
            market_name: Name of the therapeutic area or market being tracked.
        """
        self.market_name = market_name
        self.records: List[Dict] = []

    # ------------------------------------------------------------------
    # Data entry
    # ------------------------------------------------------------------

    def record_sales(
        self,
        brand: str,
        channel: str,
        period: str,
        units: float,
        value_usd: float = 0.0,
    ) -> None:
        """
        Record a brand's sales observation for one period and channel.

        Args:
            brand: Brand or generic drug name.
            channel: Distribution channel (e.g., ``Hospital``, ``Retail``).
            period: Period label (e.g., ``2025-Q1``, ``2025-01``).
            units: Units sold (packs, vials, etc.).
            value_usd: Sales value in USD (optional; used for value-based share).

        Raises:
            ValueError: If units or value_usd are negative.
        """
        if units < 0:
            raise ValueError(f"units cannot be negative (got {units})")
        if value_usd < 0:
            raise ValueError(f"value_usd cannot be negative (got {value_usd})")
        if not brand.strip():
            raise ValueError("brand cannot be empty.")
        if not period.strip():
            raise ValueError("period cannot be empty.")

        self.records.append({
            "brand": brand,
            "channel": channel,
            "period": period,
            "units": float(units),
            "value_usd": float(value_usd),
        })

    def record_bulk(self, rows: List[Dict]) -> int:
        """
        Bulk-record multiple sales observations.

        Args:
            rows: List of dicts with keys: ``brand``, ``channel``, ``period``,
                ``units``, and optionally ``value_usd``.

        Returns:
            Number of records added.

        Raises:
            KeyError: If required fields are missing.
        """
        for row in rows:
            self.record_sales(
                brand=row["brand"],
                channel=row["channel"],
                period=row["period"],
                units=row["units"],
                value_usd=row.get("value_usd", 0.0),
            )
        return len(rows)

    # ------------------------------------------------------------------
    # Market share computation
    # ------------------------------------------------------------------

    def market_share_by_period(
        self,
        channel: Optional[str] = None,
        metric: str = "units",
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate market share (%) per brand for each period.

        Args:
            channel: Filter to a specific channel. ``None`` = all channels combined.
            metric: ``"units"`` or ``"value_usd"`` for volume vs value share.

        Returns:
            Nested dict: ``{period: {brand: share_pct, ...}, ...}``

        Raises:
            ValueError: If metric is not ``"units"`` or ``"value_usd"``.
        """
        if metric not in ("units", "value_usd"):
            raise ValueError("metric must be 'units' or 'value_usd'")

        filtered = self.records if channel is None else [
            r for r in self.records if r["channel"] == channel
        ]

        # Group by period
        period_brand: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for r in filtered:
            period_brand[r["period"]][r["brand"]] += r[metric]

        result: Dict[str, Dict[str, float]] = {}
        for period, brands in sorted(period_brand.items()):
            total = sum(brands.values())
            if total == 0:
                result[period] = {b: 0.0 for b in brands}
            else:
                result[period] = {
                    b: round(v / total * 100, 2)
                    for b, v in sorted(brands.items(), key=lambda x: -x[1])
                }
        return result

    def share_trend(
        self,
        brand: str,
        channel: Optional[str] = None,
        metric: str = "units",
    ) -> Dict:
        """
        Return the market share trend for a specific brand over all periods.

        Args:
            brand: Brand name to track.
            channel: Optional channel filter.
            metric: ``"units"`` or ``"value_usd"``.

        Returns:
            dict with:

            - ``brand`` – brand name
            - ``periods`` – list of period labels
            - ``shares`` – list of market share percentages (aligned to periods)
            - ``avg_share_pct`` – mean share across periods
            - ``trend_direction`` – ``"rising"``, ``"falling"``, or ``"stable"``
            - ``delta_pp`` – change in share from first to last period (percentage points)
        """
        shares_by_period = self.market_share_by_period(channel=channel, metric=metric)
        periods = sorted(shares_by_period.keys())
        shares = [shares_by_period[p].get(brand, 0.0) for p in periods]

        if not shares:
            return {"brand": brand, "periods": [], "shares": [], "avg_share_pct": 0.0}

        avg = round(sum(shares) / len(shares), 2)
        delta = round(shares[-1] - shares[0], 2) if len(shares) > 1 else 0.0

        if delta > 1.0:
            direction = "rising"
        elif delta < -1.0:
            direction = "falling"
        else:
            direction = "stable"

        return {
            "brand": brand,
            "channel": channel or "All",
            "metric": metric,
            "periods": periods,
            "shares": shares,
            "avg_share_pct": avg,
            "trend_direction": direction,
            "delta_pp": delta,
        }

    def top_brands(
        self,
        period: str,
        channel: Optional[str] = None,
        metric: str = "units",
        top_n: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Return the top N brands by market share in a given period.

        Args:
            period: Period to query (must match a recorded period label).
            channel: Optional channel filter.
            metric: ``"units"`` or ``"value_usd"``.
            top_n: Number of top brands to return.

        Returns:
            List of ``(brand, share_pct)`` tuples sorted by share descending.

        Raises:
            KeyError: If period is not found.
        """
        shares_by_period = self.market_share_by_period(channel=channel, metric=metric)
        if period not in shares_by_period:
            raise KeyError(f"Period '{period}' not found in records.")
        brands = sorted(shares_by_period[period].items(), key=lambda x: -x[1])
        return brands[:top_n]

    def competitive_landscape(
        self, period: str, channel: Optional[str] = None
    ) -> Dict:
        """
        Return a competitive landscape snapshot for a given period.

        Args:
            period: Period label.
            channel: Optional channel filter.

        Returns:
            dict with:

            - ``leader`` – brand with highest unit share
            - ``leader_share_pct`` – leader's market share
            - ``n_brands`` – number of competing brands
            - ``herfindahl_index`` – HHI (market concentration; 0=low, 10000=monopoly)
            - ``top_3_combined_pct`` – combined share of top 3 brands
        """
        shares_by_period = self.market_share_by_period(channel=channel, metric="units")
        if period not in shares_by_period:
            raise KeyError(f"Period '{period}' not found.")

        brands = shares_by_period[period]
        if not brands:
            return {"leader": None, "leader_share_pct": 0.0, "n_brands": 0}

        sorted_brands = sorted(brands.items(), key=lambda x: -x[1])
        leader, leader_share = sorted_brands[0]
        hhi = round(sum((s / 100) ** 2 * 10000 for s in brands.values()), 0)
        top3 = round(sum(s for _, s in sorted_brands[:3]), 2)

        return {
            "period": period,
            "channel": channel or "All",
            "leader": leader,
            "leader_share_pct": leader_share,
            "n_brands": len(brands),
            "herfindahl_index": hhi,
            "top_3_combined_pct": top3,
        }

    def periods(self) -> List[str]:
        """Return sorted list of unique periods in the dataset."""
        return sorted({r["period"] for r in self.records})

    def brands(self) -> List[str]:
        """Return sorted list of unique brands in the dataset."""
        return sorted({r["brand"] for r in self.records})

    def channels(self) -> List[str]:
        """Return sorted list of unique channels in the dataset."""
        return sorted({r["channel"] for r in self.records})

    def __len__(self) -> int:
        return len(self.records)

    def __repr__(self) -> str:
        return (
            f"MarketShareTracker(market={self.market_name!r}, "
            f"records={len(self.records)}, periods={len(self.periods())})"
        )
