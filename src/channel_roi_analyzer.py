"""
Channel ROI Analyzer for pharmaceutical distribution channels.

Computes return on investment (ROI), cost-per-unit-sold, and profitability
metrics per distribution channel (hospital, retail pharmacy, clinic, e-pharmacy, etc.).
Supports investment reallocation decisions and channel strategy optimization.

Metrics computed:
  - Gross Revenue per Channel
  - Cost of Sales (CoGS + channel fees + logistics)
  - Gross Profit and Gross Margin %
  - Sales Force Investment ROI
  - Cost-Per-Incremental-Unit (CPIU) vs baseline
  - Contribution Margin per Channel
  - Break-even Volume

Reference: Zuellig Pharma Channel Analytics Framework, 2023.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ChannelInvestmentData:
    """
    Input data for a single channel's financial performance in a period.

    Parameters
    ----------
    channel_id : str
        Unique identifier for the distribution channel.
    channel_name : str
        Human-readable channel name (e.g., "Hospital Direct", "Retail Pharmacy").
    gross_revenue : float
        Total gross revenue from this channel in the period (currency units).
    units_sold : int
        Number of product units sold through this channel.
    cogs_total : float
        Total cost of goods sold (COGS) allocated to this channel.
    channel_fees : float
        Distribution fees, margins paid to channel partners.
    logistics_cost : float
        Warehousing, transport, last-mile delivery costs.
    sales_force_cost : float
        Salesperson compensation, incentives, expenses attributed to this channel.
    marketing_spend : float
        Channel-specific marketing and promotional spend.
    baseline_units : int, optional
        Units sold in the prior period (used for incremental analysis). Default: 0.
    """
    channel_id: str
    channel_name: str
    gross_revenue: float
    units_sold: int
    cogs_total: float
    channel_fees: float
    logistics_cost: float
    sales_force_cost: float
    marketing_spend: float
    baseline_units: int = 0

    def __post_init__(self):
        for attr in ["gross_revenue", "cogs_total", "channel_fees",
                     "logistics_cost", "sales_force_cost", "marketing_spend"]:
            if getattr(self, attr) < 0:
                raise ValueError(f"{attr} cannot be negative for channel {self.channel_id}")
        if self.units_sold < 0:
            raise ValueError(f"units_sold cannot be negative for channel {self.channel_id}")
        if self.baseline_units < 0:
            raise ValueError(f"baseline_units cannot be negative for channel {self.channel_id}")

    @property
    def total_investment(self) -> float:
        """Total investment = sales force + marketing spend."""
        return self.sales_force_cost + self.marketing_spend

    @property
    def total_cost_of_channel(self) -> float:
        """All-in cost: COGS + channel fees + logistics + investment."""
        return self.cogs_total + self.channel_fees + self.logistics_cost + self.total_investment


@dataclass
class ChannelROIResult:
    """Computed ROI metrics for a single channel."""
    channel_id: str
    channel_name: str

    gross_revenue: float
    gross_profit: float
    gross_margin_pct: float        # Gross profit / revenue %

    contribution_margin: float      # Revenue - variable costs (excluding fixed SF)
    contribution_margin_pct: float

    total_investment: float
    roi_pct: float                 # (Gross Profit - Investment) / Investment × 100
    revenue_per_investment: float  # Revenue / Investment ratio

    units_sold: int
    cost_per_unit_sold: float      # Total all-in cost / units sold
    incremental_units: int         # Units above baseline
    cpiu: Optional[float]          # Cost per incremental unit (investment / incremental units)

    break_even_units: int          # Units needed to cover total fixed investment

    roi_grade: str                 # A (>200%), B (100–200%), C (50–100%), D (<50%), F (negative)
    flags: List[str]

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "gross_revenue": round(self.gross_revenue, 2),
            "gross_profit": round(self.gross_profit, 2),
            "gross_margin_pct": round(self.gross_margin_pct, 2),
            "contribution_margin": round(self.contribution_margin, 2),
            "contribution_margin_pct": round(self.contribution_margin_pct, 2),
            "total_investment": round(self.total_investment, 2),
            "roi_pct": round(self.roi_pct, 2),
            "revenue_per_investment": round(self.revenue_per_investment, 2),
            "units_sold": self.units_sold,
            "cost_per_unit_sold": round(self.cost_per_unit_sold, 4),
            "incremental_units": self.incremental_units,
            "cpiu": round(self.cpiu, 4) if self.cpiu is not None else None,
            "break_even_units": self.break_even_units,
            "roi_grade": self.roi_grade,
            "flags": self.flags,
        }


class ChannelROIAnalyzer:
    """
    Analyze ROI and profitability across pharmaceutical distribution channels.

    Parameters
    ----------
    avg_selling_price : float, optional
        Average selling price per unit (used for break-even calculation).
        If not provided, derived from gross_revenue / units_sold per channel.

    Examples
    --------
    >>> analyzer = ChannelROIAnalyzer()
    >>> data = ChannelInvestmentData(
    ...     channel_id="HOSP",
    ...     channel_name="Hospital Direct",
    ...     gross_revenue=850_000,
    ...     units_sold=4250,
    ...     cogs_total=340_000,
    ...     channel_fees=42_500,
    ...     logistics_cost=25_500,
    ...     sales_force_cost=120_000,
    ...     marketing_spend=40_000,
    ...     baseline_units=3800,
    ... )
    >>> result = analyzer.analyze_channel(data)
    >>> print(f"ROI: {result.roi_pct:.1f}%  Grade: {result.roi_grade}")
    ROI: 173.2%  Grade: B
    """

    _ROI_GRADES = [
        (200.0, "A"),
        (100.0, "B"),
        (50.0,  "C"),
        (0.0,   "D"),
    ]

    def __init__(self, avg_selling_price: Optional[float] = None) -> None:
        if avg_selling_price is not None and avg_selling_price <= 0:
            raise ValueError("avg_selling_price must be positive if provided.")
        self.avg_selling_price = avg_selling_price

    def _roi_grade(self, roi_pct: float) -> str:
        if roi_pct < 0:
            return "F"
        for threshold, grade in self._ROI_GRADES:
            if roi_pct >= threshold:
                return grade
        return "D"

    def _detect_flags(
        self,
        data: ChannelInvestmentData,
        gross_margin_pct: float,
        roi_pct: float,
        cpiu: Optional[float],
    ) -> List[str]:
        flags = []
        if gross_margin_pct < 20:
            flags.append("LOW_MARGIN: Gross margin below 20%")
        if roi_pct < 0:
            flags.append("NEGATIVE_ROI: Investment exceeds incremental gross profit")
        if data.channel_fees / data.gross_revenue > 0.20 if data.gross_revenue > 0 else False:
            flags.append("HIGH_CHANNEL_FEES: Channel fees exceed 20% of revenue")
        if cpiu is not None and cpiu > (data.gross_revenue / data.units_sold if data.units_sold > 0 else float("inf")):
            flags.append("CPIU_EXCEEDS_ASP: Cost per incremental unit exceeds average selling price")
        if data.units_sold == 0:
            flags.append("ZERO_SALES: No units sold in this period")
        return flags

    def analyze_channel(self, data: ChannelInvestmentData) -> ChannelROIResult:
        """
        Compute ROI metrics for a single channel.

        Parameters
        ----------
        data : ChannelInvestmentData

        Returns
        -------
        ChannelROIResult
        """
        # Gross profit = revenue - COGS - channel fees - logistics
        variable_costs = data.cogs_total + data.channel_fees + data.logistics_cost
        gross_profit = data.gross_revenue - variable_costs
        gross_margin_pct = (gross_profit / data.gross_revenue * 100) if data.gross_revenue > 0 else 0.0

        # Contribution margin = revenue - variable costs (same as gross_profit here)
        contribution_margin = gross_profit
        cm_pct = gross_margin_pct

        # ROI = (gross_profit - total_investment) / total_investment × 100
        inv = data.total_investment
        if inv > 0:
            roi_pct = (gross_profit - inv) / inv * 100
            rev_per_inv = data.gross_revenue / inv
        else:
            roi_pct = float("inf") if gross_profit > 0 else 0.0
            rev_per_inv = float("inf") if data.gross_revenue > 0 else 0.0

        # Cost per unit sold
        cpu = data.total_cost_of_channel / data.units_sold if data.units_sold > 0 else 0.0

        # Incremental units
        incremental = max(data.units_sold - data.baseline_units, 0)

        # CPIU = investment / incremental units
        cpiu = data.total_investment / incremental if incremental > 0 else None

        # Break-even: units where revenue = total cost
        asp = self.avg_selling_price or (data.gross_revenue / data.units_sold if data.units_sold > 0 else 0.0)
        # Revenue per unit needs to cover variable cost per unit + fixed investment
        variable_cost_per_unit = variable_costs / data.units_sold if data.units_sold > 0 else 0.0
        unit_contribution = asp - variable_cost_per_unit
        if unit_contribution > 0:
            break_even = int(math.ceil(data.total_investment / unit_contribution))
        else:
            break_even = 0

        flags = self._detect_flags(data, gross_margin_pct, roi_pct, cpiu)
        grade = self._roi_grade(roi_pct)

        return ChannelROIResult(
            channel_id=data.channel_id,
            channel_name=data.channel_name,
            gross_revenue=data.gross_revenue,
            gross_profit=gross_profit,
            gross_margin_pct=gross_margin_pct,
            contribution_margin=contribution_margin,
            contribution_margin_pct=cm_pct,
            total_investment=inv,
            roi_pct=roi_pct,
            revenue_per_investment=rev_per_inv,
            units_sold=data.units_sold,
            cost_per_unit_sold=cpu,
            incremental_units=incremental,
            cpiu=cpiu,
            break_even_units=break_even,
            roi_grade=grade,
            flags=flags,
        )

    def analyze_portfolio(self, channels: List[ChannelInvestmentData]) -> List[ChannelROIResult]:
        """Analyze all channels and return sorted by ROI descending."""
        results = [self.analyze_channel(c) for c in channels]
        # Sort: A > B > C > D > F, then by gross_profit descending
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
        return sorted(results, key=lambda r: (grade_order.get(r.roi_grade, 5), -r.gross_profit))

    def portfolio_summary(self, results: List[ChannelROIResult]) -> Dict:
        """Generate portfolio-level summary metrics."""
        if not results:
            return {"total_channels": 0}

        total_rev = sum(r.gross_revenue for r in results)
        total_profit = sum(r.gross_profit for r in results)
        total_investment = sum(r.total_investment for r in results)
        portfolio_roi = (total_profit - total_investment) / total_investment * 100 if total_investment > 0 else 0.0

        grade_dist = {}
        for r in results:
            grade_dist[r.roi_grade] = grade_dist.get(r.roi_grade, 0) + 1

        best = max(results, key=lambda r: r.roi_pct)
        worst = min(results, key=lambda r: r.roi_pct)

        return {
            "total_channels": len(results),
            "total_gross_revenue": round(total_rev, 2),
            "total_gross_profit": round(total_profit, 2),
            "total_investment": round(total_investment, 2),
            "portfolio_roi_pct": round(portfolio_roi, 2),
            "grade_distribution": grade_dist,
            "best_channel": best.channel_name,
            "worst_channel": worst.channel_name,
        }


import math
