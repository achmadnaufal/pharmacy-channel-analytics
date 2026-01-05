"""
Seasonal Demand Adjuster for pharmacy channel analytics.

Decomposes pharmacy channel sales data into trend, seasonal, and irregular
components to remove seasonality bias from performance comparisons. Enables
fair YoY and period-over-period comparisons without distortion from
predictable seasonal patterns (e.g., cold/flu season, year-end stockpiling,
Ramadan/holiday effects in Southeast Asian markets).

Methodology references:
- US Census Bureau (2017) X-13ARIMA-SEATS Seasonal Adjustment Programme
- Holt, C.C. (1957) Forecasting seasonals and trends by exponentially weighted
  moving averages, ONR Research Memorandum 52
- IQVIA Channel Analytics Seasonal Correction Methodology (IQVIA, 2022)
- Pharmacoeconomics & Outcomes Research — Seasonality in prescription volumes
  (Laird & Weiss, 2018)

Author: github.com/achmadnaufal
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class MonthlyChannelData:
    """Monthly sales data for a single channel.

    Attributes:
        period: Period label in 'YYYY-MM' format (e.g., '2024-01').
        channel: Channel name (e.g., 'hospital', 'retail', 'clinic', 'OTC').
        raw_sales: Unadjusted sales volume (units, value, or TRx count).
        brand: Optional brand filter identifier.
    """

    period: str    # 'YYYY-MM'
    channel: str
    raw_sales: float
    brand: Optional[str] = None


@dataclass
class SeasonalAdjustmentResult:
    """Output of seasonal decomposition for a channel.

    Attributes:
        channel: Channel name.
        brand: Brand filter, if applied.
        periods: List of period labels.
        raw_sales: Original unadjusted sales.
        trend: Smoothed trend component (centred moving average).
        seasonal_indices: Seasonal index per period (1.0 = no effect).
        adjusted_sales: Seasonally adjusted sales (raw / seasonal_index).
        irregular: Residual irregular component (adjusted / trend).
        peak_period: Period with the highest seasonal index.
        trough_period: Period with the lowest seasonal index.
        seasonal_amplitude: Difference between max and min seasonal indices.
    """

    channel: str
    brand: Optional[str]
    periods: List[str]
    raw_sales: List[float]
    trend: List[Optional[float]]
    seasonal_indices: List[float]
    adjusted_sales: List[float]
    irregular: List[Optional[float]]
    peak_period: str
    trough_period: str
    seasonal_amplitude: float


class SeasonalDemandAdjuster:
    """Decomposes monthly pharmacy channel sales into trend, seasonal, and irregular components.

    Uses a classical additive/multiplicative decomposition with centred moving
    averages (CMA) to estimate the trend, and ratio-to-moving-average (RMA)
    to compute seasonal indices normalised to average 1.0 across periods.

    The ``adjust()`` method computes seasonally adjusted sales (SA = raw / SI)
    which removes predictable seasonal swings and enables:
    - Fair month-on-month or year-on-year KPI comparisons
    - Accurate trend line extrapolation for forecasting
    - Isolation of promotional uplift from seasonal noise

    Args:
        moving_average_window: Window size for centred moving average. Default 12
            (suitable for monthly data with annual seasonality).
        min_periods_for_decomposition: Minimum number of data points required to
            compute seasonal indices. Default 24 (2 full years).

    Example::

        data = [
            MonthlyChannelData("2023-01", "retail", 1200),
            MonthlyChannelData("2023-02", "retail", 1050),
            # ... 24 months of data ...
        ]
        adjuster = SeasonalDemandAdjuster()
        result = adjuster.adjust(data, channel="retail")
        print(result.seasonal_indices)
        print(result.adjusted_sales)
    """

    def __init__(
        self,
        moving_average_window: int = 12,
        min_periods_for_decomposition: int = 24,
    ) -> None:
        if moving_average_window < 2:
            raise ValueError(
                f"moving_average_window must be ≥ 2, got {moving_average_window}."
            )
        if min_periods_for_decomposition < moving_average_window:
            raise ValueError(
                f"min_periods_for_decomposition ({min_periods_for_decomposition}) "
                f"must be ≥ moving_average_window ({moving_average_window})."
            )
        self._window = moving_average_window
        self._min_periods = min_periods_for_decomposition

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def adjust(
        self,
        data: List[MonthlyChannelData],
        channel: str,
        brand: Optional[str] = None,
    ) -> SeasonalAdjustmentResult:
        """Decompose and seasonally adjust monthly sales for a channel.

        Args:
            data: List of MonthlyChannelData records. Multi-channel/brand data
                is acceptable; this method will filter to the specified channel/brand.
            channel: Target channel to decompose.
            brand: Optional brand filter.

        Returns:
            SeasonalAdjustmentResult with trend, seasonal indices, and adjusted sales.

        Raises:
            ValueError: If filtered data has fewer than ``min_periods_for_decomposition``
                points, or if duplicate period entries are found.
        """
        # Filter and sort by period
        filtered = [
            d for d in data
            if d.channel.lower() == channel.lower()
            and (brand is None or (d.brand and d.brand.lower() == brand.lower()))
        ]

        if len(filtered) < self._min_periods:
            raise ValueError(
                f"Channel '{channel}' has only {len(filtered)} data points. "
                f"Minimum required: {self._min_periods}."
            )

        filtered.sort(key=lambda x: x.period)
        periods = [d.period for d in filtered]

        # Duplicate period check
        if len(periods) != len(set(periods)):
            raise ValueError(
                f"Duplicate period entries found for channel '{channel}'. "
                "Ensure one record per period."
            )

        sales = [d.raw_sales for d in filtered]
        n = len(sales)

        # Step 1: Centred Moving Average (trend estimation)
        trend = self._centred_moving_average(sales)

        # Step 2: Ratio-to-CMA (SI candidates)
        ratios: List[Optional[float]] = []
        for i in range(n):
            if trend[i] is not None and trend[i] > 0:
                ratios.append(sales[i] / trend[i])
            else:
                ratios.append(None)

        # Step 3: Seasonal indices — average RMA values by month-of-year
        seasonal_indices = self._compute_seasonal_indices(periods, ratios)

        # Step 4: Seasonally adjusted sales
        adjusted = [
            round(s / si, 2) if si > 0 else s
            for s, si in zip(sales, seasonal_indices)
        ]

        # Step 5: Irregular component
        irregular: List[Optional[float]] = []
        for i in range(n):
            if trend[i] is not None and trend[i] > 0:
                irregular.append(round(adjusted[i] / trend[i], 4))
            else:
                irregular.append(None)

        # Peak / trough
        max_idx = max(range(n), key=lambda i: seasonal_indices[i])
        min_idx = min(range(n), key=lambda i: seasonal_indices[i])

        return SeasonalAdjustmentResult(
            channel=channel,
            brand=brand,
            periods=periods,
            raw_sales=sales,
            trend=trend,
            seasonal_indices=seasonal_indices,
            adjusted_sales=adjusted,
            irregular=irregular,
            peak_period=periods[max_idx],
            trough_period=periods[min_idx],
            seasonal_amplitude=round(
                max(seasonal_indices) - min(seasonal_indices), 4
            ),
        )

    def compare_channels(
        self,
        data: List[MonthlyChannelData],
        channels: List[str],
        brand: Optional[str] = None,
    ) -> Dict[str, SeasonalAdjustmentResult]:
        """Adjust multiple channels and return a comparison dict.

        Args:
            data: Combined monthly data for all channels.
            channels: List of channel names to decompose.
            brand: Optional brand filter applied to all channels.

        Returns:
            Dict mapping channel name → SeasonalAdjustmentResult.
            Channels with insufficient data are excluded (no exception raised).
        """
        results: Dict[str, SeasonalAdjustmentResult] = {}
        for ch in channels:
            try:
                results[ch] = self.adjust(data, ch, brand)
            except ValueError:
                pass  # Skip channels with insufficient data
        return results

    def seasonal_index_summary(self, result: SeasonalAdjustmentResult) -> Dict:
        """Return a month-label → average SI mapping for a result.

        Collapses multi-year SI values to a single annual seasonal pattern
        (average SI per calendar month).

        Args:
            result: Output of ``adjust()``.

        Returns:
            Dict with month abbreviation keys ('Jan'–'Dec') → mean seasonal index.
        """
        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        buckets: Dict[int, List[float]] = {m: [] for m in range(1, 13)}

        for period, si in zip(result.periods, result.seasonal_indices):
            month = int(period.split("-")[1])
            buckets[month].append(si)

        return {
            month_names[m - 1]: round(sum(v) / len(v), 4) if v else 1.0
            for m, v in buckets.items()
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _centred_moving_average(self, sales: List[float]) -> List[Optional[float]]:
        """Compute centred moving average with the configured window."""
        n = len(sales)
        half = self._window // 2
        cma: List[Optional[float]] = [None] * n

        for i in range(half, n - half):
            window_vals = sales[i - half: i + half + 1]
            if len(window_vals) == self._window + 1:
                cma[i] = round(sum(window_vals) / len(window_vals), 4)
            elif len(window_vals) == self._window:
                cma[i] = round(sum(window_vals) / self._window, 4)

        return cma

    def _compute_seasonal_indices(
        self,
        periods: List[str],
        ratios: List[Optional[float]],
    ) -> List[float]:
        """Average ratio-to-CMA values by calendar month, normalise to mean 1.0."""
        month_ratios: Dict[int, List[float]] = {m: [] for m in range(1, 13)}

        for period, ratio in zip(periods, ratios):
            if ratio is not None:
                month = int(period.split("-")[1])
                month_ratios[month].append(ratio)

        raw_si: Dict[int, float] = {}
        for m, vals in month_ratios.items():
            raw_si[m] = sum(vals) / len(vals) if vals else 1.0

        # Normalise: sum of indices should equal number of periods (12 for monthly)
        total = sum(raw_si.values())
        normalised = {m: v * 12 / total for m, v in raw_si.items()}

        # Assign back per period
        return [
            round(normalised.get(int(p.split("-")[1]), 1.0), 4)
            for p in periods
        ]
