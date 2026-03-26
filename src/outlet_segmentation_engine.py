"""
Pharmacy Outlet Segmentation Engine for pharmaceutical channel analytics.

Segments pharmacy outlets (drugstores, hospital pharmacies, clinics, etc.)
into actionable tiers using multi-dimensional scoring. This supports
sales force allocation, promotional spend prioritisation, and channel
strategy design.

Segmentation dimensions:
  1. **Sales potential**: revenue size, growth trajectory, patient throughput
  2. **Strategic importance**: location type, disease area relevance, key account status
  3. **Relationship quality**: visit frequency, prescriber linkage, in-stock compliance
  4. **Operational efficiency**: order fill rate, payment terms, return rate

Methodology:
  - Weighted composite score (0–100) across dimensions
  - K-means-like rule-based tier assignment: PLATINUM / GOLD / SILVER / BRONZE
  - Coverage optimisation: recommended visit frequency per tier
  - Whitespace analysis: high-potential low-penetration outlets

Applications:
  - Sales rep territory planning and call planning
  - Key account management (KAM) prioritisation
  - Distributor performance benchmarking
  - Promo budget allocation by outlet tier

Author: github.com/achmadnaufal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class OutletType(str, Enum):
    """Pharmacy outlet type classification."""
    HOSPITAL_PHARMACY = "hospital_pharmacy"
    CHAIN_DRUGSTORE = "chain_drugstore"
    INDEPENDENT_PHARMACY = "independent_pharmacy"
    CLINIC_PHARMACY = "clinic_pharmacy"
    ONLINE_PHARMACY = "online_pharmacy"
    WHOLESALER = "wholesaler"


class OutletTier(str, Enum):
    """Outlet tier classification by composite score."""
    PLATINUM = "PLATINUM"  # Score ≥ 80
    GOLD = "GOLD"          # Score 60–79
    SILVER = "SILVER"      # Score 40–59
    BRONZE = "BRONZE"      # Score < 40


# Recommended visit frequencies (visits/month) by tier
VISIT_FREQUENCY: Dict[OutletTier, int] = {
    OutletTier.PLATINUM: 4,   # Weekly
    OutletTier.GOLD: 2,       # Bi-weekly
    OutletTier.SILVER: 1,     # Monthly
    OutletTier.BRONZE: 0,     # Outbound / distributor managed
}

# Promotional investment multipliers by tier (relative to base spend)
PROMO_MULTIPLIER: Dict[OutletTier, float] = {
    OutletTier.PLATINUM: 3.0,
    OutletTier.GOLD: 1.8,
    OutletTier.SILVER: 1.0,
    OutletTier.BRONZE: 0.4,
}

# Score thresholds
TIER_THRESHOLDS: Dict[OutletTier, float] = {
    OutletTier.PLATINUM: 80.0,
    OutletTier.GOLD: 60.0,
    OutletTier.SILVER: 40.0,
    OutletTier.BRONZE: 0.0,
}

# Dimension weights (sum to 1.0)
DIMENSION_WEIGHTS: Dict[str, float] = {
    "sales_potential": 0.40,
    "strategic_importance": 0.25,
    "relationship_quality": 0.20,
    "operational_efficiency": 0.15,
}


@dataclass
class PharmacyOutlet:
    """Data profile for a single pharmacy outlet.

    Attributes:
        outlet_id: Unique outlet identifier.
        outlet_name: Display name.
        outlet_type: Classification (hospital, chain, independent, etc.).
        city: City location.
        region: Sales region or territory.
        monthly_revenue_usd: Average monthly revenue (USD) across all brands.
        brand_revenue_usd: Monthly revenue attributable to the focal brand (USD).
        yoy_growth_pct: Year-over-year total pharmacy revenue growth (%).
        patient_throughput_daily: Average daily prescription volume (all Rx).
        is_key_account: Whether this outlet is a designated key account.
        linked_hcp_count: Number of prescribers directly linked to this outlet.
        disease_area_relevance: Relevance score to focal disease area (0–10).
        visit_frequency_actual: Actual rep visits per month.
        in_stock_compliance_pct: % of time focal brand is in-stock (0–100).
        order_fill_rate_pct: % of orders fulfilled on time (0–100).
        payment_days: Average days to payment (DSO proxy).
        return_rate_pct: Product return rate (0–100).
        current_tier: Previous tier label (if any). Used for tier migration tracking.
    """

    outlet_id: str
    outlet_name: str
    outlet_type: OutletType
    city: str
    region: str
    monthly_revenue_usd: float
    brand_revenue_usd: float
    yoy_growth_pct: float
    patient_throughput_daily: int
    is_key_account: bool = False
    linked_hcp_count: int = 0
    disease_area_relevance: float = 5.0
    visit_frequency_actual: int = 1
    in_stock_compliance_pct: float = 80.0
    order_fill_rate_pct: float = 90.0
    payment_days: int = 30
    return_rate_pct: float = 2.0
    current_tier: Optional[str] = None

    def __post_init__(self) -> None:
        if self.monthly_revenue_usd < 0:
            raise ValueError("monthly_revenue_usd cannot be negative")
        if self.brand_revenue_usd < 0:
            raise ValueError("brand_revenue_usd cannot be negative")
        if self.brand_revenue_usd > self.monthly_revenue_usd:
            raise ValueError("brand_revenue_usd cannot exceed monthly_revenue_usd")
        if not (0 <= self.disease_area_relevance <= 10):
            raise ValueError("disease_area_relevance must be 0–10")
        if not (0 <= self.in_stock_compliance_pct <= 100):
            raise ValueError("in_stock_compliance_pct must be 0–100")
        if not (0 <= self.order_fill_rate_pct <= 100):
            raise ValueError("order_fill_rate_pct must be 0–100")
        if not (0 <= self.return_rate_pct <= 100):
            raise ValueError("return_rate_pct must be 0–100")

    @property
    def brand_share_of_outlet_pct(self) -> float:
        """Brand revenue as % of total outlet revenue."""
        if self.monthly_revenue_usd == 0:
            return 0.0
        return (self.brand_revenue_usd / self.monthly_revenue_usd) * 100


@dataclass
class OutletSegmentationResult:
    """Segmentation output for a single outlet.

    Attributes:
        outlet_id: Reference outlet.
        outlet_name: Display name.
        tier: Assigned OutletTier.
        composite_score: Overall weighted score (0–100).
        dimension_scores: Per-dimension sub-scores (0–100 each).
        recommended_visits_per_month: Suggested call frequency.
        promo_budget_multiplier: Relative promotional investment vs base.
        is_whitespace: True if high-potential outlet with low brand penetration.
        tier_change: 'UP', 'DOWN', 'STABLE', or 'NEW' vs previous tier.
        action_items: Specific commercial actions for this outlet.
    """

    outlet_id: str
    outlet_name: str
    tier: OutletTier
    composite_score: float
    dimension_scores: Dict[str, float]
    recommended_visits_per_month: int
    promo_budget_multiplier: float
    is_whitespace: bool
    tier_change: str
    action_items: List[str]


class OutletSegmentationEngine:
    """Segments pharmacy outlets into commercial tiers using weighted scoring.

    Supports territory planning, promo budget allocation, and whitespace
    analysis across a portfolio of pharmacy accounts.

    Example:
        >>> engine = OutletSegmentationEngine()
        >>> outlet = PharmacyOutlet(
        ...     outlet_id="PH_JKT_001",
        ...     outlet_name="Kimia Farma Salemba",
        ...     outlet_type=OutletType.CHAIN_DRUGSTORE,
        ...     city="Jakarta",
        ...     region="Java West",
        ...     monthly_revenue_usd=45_000,
        ...     brand_revenue_usd=3_200,
        ...     yoy_growth_pct=18,
        ...     patient_throughput_daily=250,
        ...     linked_hcp_count=12,
        ... )
        >>> result = engine.segment(outlet)
        >>> print(result.tier)
        OutletTier.GOLD
    """

    def __init__(
        self,
        revenue_benchmark_usd: float = 20_000,
        high_growth_threshold_pct: float = 15.0,
        whitespace_penetration_threshold_pct: float = 5.0,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """Initialise the engine.

        Args:
            revenue_benchmark_usd: Monthly revenue used as 100-point reference.
            high_growth_threshold_pct: Growth rate above which outlet gets growth bonus.
            whitespace_penetration_threshold_pct: Brand share below this = whitespace outlet.
            weights: Optional override for dimension weights (must sum to 1.0).
        """
        self.revenue_benchmark_usd = revenue_benchmark_usd
        self.high_growth_threshold_pct = high_growth_threshold_pct
        self.whitespace_penetration_threshold_pct = whitespace_penetration_threshold_pct
        self.weights = weights or DIMENSION_WEIGHTS
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Dimension weights must sum to 1.0, got {total:.3f}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(self, outlet: PharmacyOutlet) -> OutletSegmentationResult:
        """Segment a single pharmacy outlet.

        Args:
            outlet: PharmacyOutlet data profile.

        Returns:
            OutletSegmentationResult with tier, scores, and action items.
        """
        if not isinstance(outlet, PharmacyOutlet):
            raise TypeError("outlet must be a PharmacyOutlet instance")

        dim_scores = {
            "sales_potential": self._score_sales_potential(outlet),
            "strategic_importance": self._score_strategic_importance(outlet),
            "relationship_quality": self._score_relationship_quality(outlet),
            "operational_efficiency": self._score_operational_efficiency(outlet),
        }

        composite = sum(
            dim_scores[dim] * self.weights[dim] for dim in dim_scores
        )
        tier = self._assign_tier(composite)
        is_ws = self._is_whitespace(outlet)
        tier_change = self._detect_tier_change(outlet.current_tier, tier)
        actions = self._generate_actions(outlet, tier, is_ws, dim_scores)

        return OutletSegmentationResult(
            outlet_id=outlet.outlet_id,
            outlet_name=outlet.outlet_name,
            tier=tier,
            composite_score=round(composite, 1),
            dimension_scores={k: round(v, 1) for k, v in dim_scores.items()},
            recommended_visits_per_month=VISIT_FREQUENCY[tier],
            promo_budget_multiplier=PROMO_MULTIPLIER[tier],
            is_whitespace=is_ws,
            tier_change=tier_change,
            action_items=actions,
        )

    def segment_portfolio(
        self, outlets: List[PharmacyOutlet]
    ) -> List[OutletSegmentationResult]:
        """Segment a full portfolio of outlets.

        Args:
            outlets: List of PharmacyOutlet profiles.

        Returns:
            List of OutletSegmentationResult, sorted by composite score descending.

        Raises:
            ValueError: If outlets list is empty.
        """
        if not outlets:
            raise ValueError("outlets list cannot be empty")
        results = [self.segment(o) for o in outlets]
        return sorted(results, key=lambda r: r.composite_score, reverse=True)

    def portfolio_summary(
        self, results: List[OutletSegmentationResult]
    ) -> Dict:
        """Aggregate tier distribution and KPI summary for a portfolio.

        Args:
            results: List of OutletSegmentationResult.

        Returns:
            Dict with tier counts, whitespace count, and recommended total visits.
        """
        by_tier: Dict[str, int] = {t.value: 0 for t in OutletTier}
        for r in results:
            by_tier[r.tier.value] += 1

        total_recommended_visits = sum(r.recommended_visits_per_month for r in results)
        whitespace_count = sum(1 for r in results if r.is_whitespace)
        upgrades = sum(1 for r in results if r.tier_change == "UP")
        downgrades = sum(1 for r in results if r.tier_change == "DOWN")

        return {
            "total_outlets": len(results),
            "tier_distribution": by_tier,
            "whitespace_outlets": whitespace_count,
            "total_monthly_visits_recommended": total_recommended_visits,
            "tier_upgrades": upgrades,
            "tier_downgrades": downgrades,
            "avg_composite_score": round(sum(r.composite_score for r in results) / len(results), 1),
        }

    # ------------------------------------------------------------------
    # Private scoring methods
    # ------------------------------------------------------------------

    def _score_sales_potential(self, outlet: PharmacyOutlet) -> float:
        """Score sales potential 0–100."""
        # Revenue component (0–60)
        rev_score = min(60, (outlet.monthly_revenue_usd / self.revenue_benchmark_usd) * 60)
        # Growth component (0–25)
        growth_score = min(25, max(0, outlet.yoy_growth_pct * 0.8))
        if outlet.yoy_growth_pct >= self.high_growth_threshold_pct:
            growth_score = min(25, growth_score * 1.2)  # 20% bonus for high growth
        # Patient throughput (0–15)
        throughput_score = min(15, outlet.patient_throughput_daily / 20)
        return rev_score + growth_score + throughput_score

    def _score_strategic_importance(self, outlet: PharmacyOutlet) -> float:
        """Score strategic importance 0–100."""
        score = 0.0
        # Key account status (0–30)
        if outlet.is_key_account:
            score += 30
        # Outlet type strategic value (0–30)
        type_scores = {
            OutletType.HOSPITAL_PHARMACY: 30,
            OutletType.CHAIN_DRUGSTORE: 25,
            OutletType.CLINIC_PHARMACY: 20,
            OutletType.INDEPENDENT_PHARMACY: 12,
            OutletType.ONLINE_PHARMACY: 15,
            OutletType.WHOLESALER: 10,
        }
        score += type_scores.get(outlet.outlet_type, 10)
        # HCP linkage (0–20)
        score += min(20, outlet.linked_hcp_count * 2)
        # Disease area relevance (0–20)
        score += outlet.disease_area_relevance * 2
        return min(100, score)

    def _score_relationship_quality(self, outlet: PharmacyOutlet) -> float:
        """Score relationship quality 0–100."""
        # Visit frequency (0–40): compare actual to recommended
        ideal_freq = 2  # baseline expectation
        visit_score = min(40, (outlet.visit_frequency_actual / ideal_freq) * 40)
        # In-stock compliance (0–35)
        stock_score = outlet.in_stock_compliance_pct * 0.35
        # HCP relationship proxy via linked count (0–25)
        hcp_rel_score = min(25, outlet.linked_hcp_count * 2.5)
        return visit_score + stock_score + hcp_rel_score

    def _score_operational_efficiency(self, outlet: PharmacyOutlet) -> float:
        """Score operational efficiency 0–100."""
        # Fill rate (0–40)
        fill_score = outlet.order_fill_rate_pct * 0.40
        # Payment speed (0–35): DSO < 15 days = full points; >60 = 0
        payment_score = max(0, 35 - (outlet.payment_days - 15) * 0.78)
        payment_score = min(35, payment_score)
        # Return rate penalty (0–25): 0% returns = 25pts; 10%+ = 0pts
        return_score = max(0, 25 - outlet.return_rate_pct * 2.5)
        return fill_score + payment_score + return_score

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _assign_tier(score: float) -> OutletTier:
        if score >= TIER_THRESHOLDS[OutletTier.PLATINUM]:
            return OutletTier.PLATINUM
        elif score >= TIER_THRESHOLDS[OutletTier.GOLD]:
            return OutletTier.GOLD
        elif score >= TIER_THRESHOLDS[OutletTier.SILVER]:
            return OutletTier.SILVER
        else:
            return OutletTier.BRONZE

    def _is_whitespace(self, outlet: PharmacyOutlet) -> bool:
        """True if outlet has high potential but low brand penetration."""
        high_potential = outlet.monthly_revenue_usd >= self.revenue_benchmark_usd * 0.5
        low_penetration = outlet.brand_share_of_outlet_pct < self.whitespace_penetration_threshold_pct
        return high_potential and low_penetration

    @staticmethod
    def _detect_tier_change(prev_tier_str: Optional[str], new_tier: OutletTier) -> str:
        if prev_tier_str is None:
            return "NEW"
        tier_order = [OutletTier.BRONZE, OutletTier.SILVER, OutletTier.GOLD, OutletTier.PLATINUM]
        try:
            prev = OutletTier(prev_tier_str.upper())
        except (ValueError, AttributeError):
            return "NEW"
        prev_idx = tier_order.index(prev)
        new_idx = tier_order.index(new_tier)
        if new_idx > prev_idx:
            return "UP"
        elif new_idx < prev_idx:
            return "DOWN"
        return "STABLE"

    @staticmethod
    def _generate_actions(
        outlet: PharmacyOutlet,
        tier: OutletTier,
        is_whitespace: bool,
        dim_scores: Dict[str, float],
    ) -> List[str]:
        actions: List[str] = []
        if is_whitespace:
            actions.append(
                f"Whitespace opportunity: brand penetration at "
                f"{outlet.brand_share_of_outlet_pct:.1f}% — target rep activation campaign."
            )
        if dim_scores.get("operational_efficiency", 100) < 50:
            actions.append("Low operational efficiency: review order fill rate and payment terms with distributor.")
        if outlet.in_stock_compliance_pct < 80:
            actions.append(f"In-stock compliance at {outlet.in_stock_compliance_pct:.0f}% — trigger replenishment SOP review.")
        if tier == OutletTier.PLATINUM and outlet.linked_hcp_count < 5:
            actions.append("Platinum outlet with few linked HCPs — prioritise prescriber engagement programmes.")
        if tier == OutletTier.BRONZE:
            actions.append("Bronze tier — route through distributor; remove from direct rep call plan.")
        if not actions:
            actions.append("Maintain current engagement plan; monitor for tier migration signals.")
        return actions
