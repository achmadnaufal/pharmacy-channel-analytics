"""
Pharmacy channel mix optimisation module.

Recommends optimal resource allocation across pharmacy channels (retail, hospital,
clinic, e-commerce) using a return-on-investment (ROI) maximisation approach.
Supports channel investment planning for pharma commercial teams.

Methodology:
  - Channel efficiency scoring: revenue/investment ratio adjusted for strategic weight
  - Diminishing returns modelling: marginal ROI declines as investment increases
  - Budget reallocation: moves budget from underperforming to high-ROI channels
  - Scenario comparison: current vs optimised allocation

References:
  - Kotler & Keller (2016) Marketing Management, Ch. 15 — Channel Management
  - McKinsey Pharma Omnichannel Benchmarking Study (2023)
  - IQVIA Multichannel HCP Engagement Analytics framework
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Default strategic weights by channel type
# Higher weight = channel is strategically prioritised beyond pure ROI
DEFAULT_CHANNEL_WEIGHTS: Dict[str, float] = {
    "hospital_pharmacy":   1.30,   # Key account, high-value patients
    "retail_pharmacy":     1.00,   # Standard weight
    "clinic_dispensary":   1.10,   # HCP relationship proximity
    "e_commerce":          0.90,   # Growing but not yet primary for Rx
    "specialty_pharmacy":  1.25,   # Specialty/biologic brands
    "modern_trade":        0.85,   # OTC / consumer health focus
}


@dataclass
class ChannelMetrics:
    """
    Performance metrics for a single pharmacy channel.

    Attributes:
        channel_id (str): Unique channel identifier
        channel_type (str): Channel category (e.g., 'hospital_pharmacy')
        current_investment_usd (float): Current monthly investment (USD)
        current_revenue_usd (float): Current monthly revenue from channel (USD)
        growth_rate_pct (float): Monthly revenue growth rate (%)
        strategic_weight (float): Strategic importance multiplier (default 1.0)
        fixed_cost_usd (float): Non-variable channel maintenance cost (USD/month)

    Example:
        >>> ch = ChannelMetrics(
        ...     channel_id="CH-001",
        ...     channel_type="hospital_pharmacy",
        ...     current_investment_usd=50_000,
        ...     current_revenue_usd=380_000,
        ... )
        >>> print(ch.roi)
    """

    channel_id: str
    channel_type: str
    current_investment_usd: float
    current_revenue_usd: float
    growth_rate_pct: float = 0.0
    strategic_weight: float = 1.0
    fixed_cost_usd: float = 0.0

    def __post_init__(self):
        if not self.channel_id.strip():
            raise ValueError("channel_id cannot be empty")
        if self.current_investment_usd < 0:
            raise ValueError("current_investment_usd cannot be negative")
        if self.current_revenue_usd < 0:
            raise ValueError("current_revenue_usd cannot be negative")
        if self.strategic_weight <= 0:
            raise ValueError("strategic_weight must be positive")
        # Default strategic weight from catalogue if available
        if self.strategic_weight == 1.0 and self.channel_type in DEFAULT_CHANNEL_WEIGHTS:
            self.strategic_weight = DEFAULT_CHANNEL_WEIGHTS[self.channel_type]

    @property
    def roi(self) -> float:
        """
        Simple ROI: (revenue - investment) / investment.

        Returns:
            ROI as decimal (e.g., 2.5 = 250% return).
            Returns 0.0 if investment is 0.
        """
        if self.current_investment_usd == 0:
            return 0.0
        return (self.current_revenue_usd - self.current_investment_usd) / self.current_investment_usd

    @property
    def revenue_per_dollar(self) -> float:
        """Revenue generated per dollar invested."""
        if self.current_investment_usd == 0:
            return 0.0
        return self.current_revenue_usd / self.current_investment_usd

    @property
    def weighted_efficiency(self) -> float:
        """
        Strategic-weight-adjusted efficiency score.

        Combines ROI with growth rate and strategic weight to produce
        a composite channel efficiency score used for allocation ranking.

        Returns:
            Weighted efficiency score (higher = more attractive channel)
        """
        base_efficiency = self.revenue_per_dollar
        growth_boost = 1.0 + max(0.0, self.growth_rate_pct / 100.0)
        return base_efficiency * self.strategic_weight * growth_boost


@dataclass
class AllocationResult:
    """
    Optimised budget allocation for a single channel.

    Attributes:
        channel_id (str): Channel identifier
        channel_type (str): Channel category
        current_investment_usd (float): Original investment
        recommended_investment_usd (float): Optimised investment
        investment_change_usd (float): Delta (positive = increase)
        investment_change_pct (float): Percentage change
        projected_revenue_usd (float): Estimated revenue under new allocation
        projected_roi (float): Estimated ROI under new allocation
        recommendation (str): Human-readable rationale
    """

    channel_id: str
    channel_type: str
    current_investment_usd: float
    recommended_investment_usd: float
    investment_change_usd: float
    investment_change_pct: float
    projected_revenue_usd: float
    projected_roi: float
    recommendation: str


class ChannelMixOptimizer:
    """
    Optimise budget allocation across pharmacy channels to maximise ROI.

    Uses a diminishing-returns model: each additional dollar invested in a
    channel yields progressively less marginal revenue, modelled via a
    square-root (concave) function. Budget is iteratively reallocated from
    lower-efficiency to higher-efficiency channels.

    Args:
        channels (List[ChannelMetrics]): List of channel performance metrics
        total_budget_usd (float): Total monthly budget to allocate
        min_channel_allocation_pct (float): Minimum fraction of budget per channel
            (prevents zeroing out any channel; default 0.05 = 5%)
        max_channel_allocation_pct (float): Maximum fraction of budget per channel
            (prevents over-concentration; default 0.50 = 50%)

    Example:
        >>> channels = [
        ...     ChannelMetrics("CH-001", "hospital_pharmacy", 50000, 380000, 5.2),
        ...     ChannelMetrics("CH-002", "retail_pharmacy",   80000, 240000, 1.8),
        ...     ChannelMetrics("CH-003", "e_commerce",        20000,  95000, 12.0),
        ... ]
        >>> optimizer = ChannelMixOptimizer(channels, total_budget_usd=150000)
        >>> results = optimizer.optimise()
        >>> for r in results:
        ...     print(f"{r.channel_id}: ${r.recommended_investment_usd:,.0f} "
        ...           f"({r.investment_change_pct:+.1f}%)")
    """

    def __init__(
        self,
        channels: List[ChannelMetrics],
        total_budget_usd: float,
        min_channel_allocation_pct: float = 0.05,
        max_channel_allocation_pct: float = 0.50,
    ):
        if not channels:
            raise ValueError("channels list cannot be empty")
        if total_budget_usd <= 0:
            raise ValueError("total_budget_usd must be positive")
        if not 0.0 <= min_channel_allocation_pct < max_channel_allocation_pct <= 1.0:
            raise ValueError(
                "min_channel_allocation_pct must be in [0, max) and max must be <= 1"
            )
        n = len(channels)
        if min_channel_allocation_pct * n > 1.0:
            raise ValueError(
                f"min_channel_allocation_pct × n_channels ({min_channel_allocation_pct} × {n}) "
                "exceeds 1.0 — impossible to satisfy all minimums"
            )

        self.channels = channels
        self.total_budget_usd = total_budget_usd
        self.min_allocation = min_channel_allocation_pct
        self.max_allocation = max_channel_allocation_pct

    def _marginal_revenue(self, channel: ChannelMetrics, investment: float) -> float:
        """
        Estimate revenue at a given investment level using diminishing returns.

        Model: R(I) = R_0 × sqrt(I / I_0)
        Where R_0 = current revenue, I_0 = current investment.

        This square-root model ensures marginal returns decrease with scale,
        consistent with empirical channel ROI curves.

        Args:
            channel: The channel to evaluate
            investment: Hypothetical investment level (USD)

        Returns:
            Estimated revenue at the given investment level
        """
        if channel.current_investment_usd == 0:
            # No baseline: use conservative linear estimate
            return investment * 2.0
        ratio = investment / channel.current_investment_usd
        return channel.current_revenue_usd * math.sqrt(ratio)

    def optimise(self) -> List[AllocationResult]:
        """
        Compute optimal budget allocation across all channels.

        Algorithm:
        1. Rank channels by weighted efficiency score (descending)
        2. Assign minimum budget to all channels (floor allocation)
        3. Distribute remaining budget proportionally to efficiency scores,
           capped at max allocation per channel
        4. Project revenue under new allocation using diminishing returns model

        Returns:
            List of AllocationResult, one per channel, sorted by recommended investment descending

        Example:
            >>> results = optimizer.optimise()
            >>> total_projected = sum(r.projected_revenue_usd for r in results)
            >>> print(f"Total projected revenue: ${total_projected:,.0f}")
        """
        n = len(self.channels)
        budget = self.total_budget_usd
        min_budget = self.min_allocation * budget
        max_budget = self.max_allocation * budget

        # Step 1: Floor allocation
        remaining = budget - min_budget * n

        # Step 2: Score-proportional distribution of remaining budget
        scores = [ch.weighted_efficiency for ch in self.channels]
        total_score = sum(scores)

        if total_score == 0:
            # All channels have zero efficiency — split equally
            proportional = [remaining / n] * n
        else:
            proportional = [remaining * (s / total_score) for s in scores]

        # Step 3: Apply max cap — overflow redistributed to uncapped channels
        allocations = [min_budget + p for p in proportional]
        for _ in range(10):  # iterate to handle cascading caps
            capped = [min(a, max_budget) for a in allocations]
            overflow = sum(a - c for a, c in zip(allocations, capped))
            if overflow < 1.0:
                allocations = capped
                break
            # Redistribute overflow to uncapped channels
            uncapped_idx = [i for i, a in enumerate(allocations) if a < max_budget]
            if not uncapped_idx:
                allocations = capped
                break
            uncapped_scores = [scores[i] for i in uncapped_idx]
            uncapped_total = sum(uncapped_scores)
            for i in uncapped_idx:
                share = (scores[i] / uncapped_total) if uncapped_total > 0 else 1.0 / len(uncapped_idx)
                allocations[i] = min(max_budget, capped[i] + overflow * share)

        # Ensure total sums to budget (fix floating-point drift)
        total_alloc = sum(allocations)
        if abs(total_alloc - budget) > 0.01:
            diff = budget - total_alloc
            # Add diff to the highest-allocation channel
            max_idx = allocations.index(max(allocations))
            allocations[max_idx] += diff

        results = []
        for ch, alloc in zip(self.channels, allocations):
            projected_rev = self._marginal_revenue(ch, alloc)
            projected_roi = (projected_rev - alloc) / alloc if alloc > 0 else 0.0
            change = alloc - ch.current_investment_usd
            change_pct = (change / ch.current_investment_usd * 100) if ch.current_investment_usd > 0 else 0.0

            if change > 500:
                recommendation = f"Increase investment — high efficiency score ({ch.weighted_efficiency:.2f})"
            elif change < -500:
                recommendation = f"Reduce investment — lower efficiency; reallocate to higher-ROI channels"
            else:
                recommendation = "Maintain current investment — near-optimal allocation"

            results.append(
                AllocationResult(
                    channel_id=ch.channel_id,
                    channel_type=ch.channel_type,
                    current_investment_usd=round(ch.current_investment_usd, 2),
                    recommended_investment_usd=round(alloc, 2),
                    investment_change_usd=round(change, 2),
                    investment_change_pct=round(change_pct, 1),
                    projected_revenue_usd=round(projected_rev, 2),
                    projected_roi=round(projected_roi, 4),
                    recommendation=recommendation,
                )
            )

        return sorted(results, key=lambda r: r.recommended_investment_usd, reverse=True)

    def portfolio_summary(self) -> Dict:
        """
        Summary of current vs optimised portfolio metrics.

        Returns:
            Dict with:
                - current_total_revenue (float): Sum of current channel revenues
                - projected_total_revenue (float): Sum of projected revenues
                - revenue_uplift_usd (float): Projected incremental revenue
                - revenue_uplift_pct (float): % improvement
                - current_portfolio_roi (float): Current blended ROI
                - projected_portfolio_roi (float): Projected blended ROI
                - n_channels_increased (int): Channels receiving more budget
                - n_channels_decreased (int): Channels receiving less budget

        Example:
            >>> summary = optimizer.portfolio_summary()
            >>> print(f"Revenue uplift: +${summary['revenue_uplift_usd']:,.0f}")
        """
        results = self.optimise()
        current_revenue = sum(ch.current_revenue_usd for ch in self.channels)
        projected_revenue = sum(r.projected_revenue_usd for r in results)
        current_investment = sum(ch.current_investment_usd for ch in self.channels)
        current_roi = (
            (current_revenue - current_investment) / current_investment
            if current_investment > 0 else 0.0
        )
        projected_roi = (
            (projected_revenue - self.total_budget_usd) / self.total_budget_usd
            if self.total_budget_usd > 0 else 0.0
        )
        n_increased = sum(1 for r in results if r.investment_change_usd > 500)
        n_decreased = sum(1 for r in results if r.investment_change_usd < -500)

        return {
            "current_total_revenue": round(current_revenue, 2),
            "projected_total_revenue": round(projected_revenue, 2),
            "revenue_uplift_usd": round(projected_revenue - current_revenue, 2),
            "revenue_uplift_pct": round(
                (projected_revenue - current_revenue) / current_revenue * 100, 2
            ) if current_revenue > 0 else 0.0,
            "current_portfolio_roi": round(current_roi, 4),
            "projected_portfolio_roi": round(projected_roi, 4),
            "n_channels_increased": n_increased,
            "n_channels_decreased": n_decreased,
            "total_budget_usd": self.total_budget_usd,
        }
