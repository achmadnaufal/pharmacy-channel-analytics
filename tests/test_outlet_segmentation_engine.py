"""Unit tests for OutletSegmentationEngine."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from outlet_segmentation_engine import (
    OutletSegmentationEngine,
    PharmacyOutlet,
    OutletType,
    OutletTier,
    VISIT_FREQUENCY,
    PROMO_MULTIPLIER,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_outlet(
    outlet_id="PH_001",
    outlet_type=OutletType.CHAIN_DRUGSTORE,
    monthly_revenue=45_000,
    brand_revenue=3_200,
    yoy_growth=18.0,
    throughput=250,
    is_key_account=False,
    linked_hcp=5,
    da_relevance=7.0,
    visit_freq=2,
    in_stock=90.0,
    fill_rate=95.0,
    payment_days=20,
    return_rate=1.5,
    current_tier=None,
) -> PharmacyOutlet:
    return PharmacyOutlet(
        outlet_id=outlet_id,
        outlet_name=f"Outlet {outlet_id}",
        outlet_type=outlet_type,
        city="Jakarta",
        region="Java West",
        monthly_revenue_usd=monthly_revenue,
        brand_revenue_usd=brand_revenue,
        yoy_growth_pct=yoy_growth,
        patient_throughput_daily=throughput,
        is_key_account=is_key_account,
        linked_hcp_count=linked_hcp,
        disease_area_relevance=da_relevance,
        visit_frequency_actual=visit_freq,
        in_stock_compliance_pct=in_stock,
        order_fill_rate_pct=fill_rate,
        payment_days=payment_days,
        return_rate_pct=return_rate,
        current_tier=current_tier,
    )


# ---------------------------------------------------------------------------
# PharmacyOutlet validation
# ---------------------------------------------------------------------------

class TestPharmacyOutlet:
    def test_brand_share(self):
        o = make_outlet(monthly_revenue=10_000, brand_revenue=500)
        assert abs(o.brand_share_of_outlet_pct - 5.0) < 0.01

    def test_negative_revenue_raises(self):
        with pytest.raises(ValueError):
            make_outlet(monthly_revenue=-1)

    def test_brand_exceeds_total_raises(self):
        with pytest.raises(ValueError):
            make_outlet(monthly_revenue=1_000, brand_revenue=2_000)

    def test_invalid_da_relevance_raises(self):
        with pytest.raises(ValueError):
            make_outlet(da_relevance=15)

    def test_invalid_in_stock_raises(self):
        with pytest.raises(ValueError):
            make_outlet(in_stock=110)


# ---------------------------------------------------------------------------
# OutletSegmentationEngine
# ---------------------------------------------------------------------------

class TestSegmentationEngine:
    def setup_method(self):
        self.engine = OutletSegmentationEngine(revenue_benchmark_usd=20_000)

    def test_high_value_outlet_gold_or_platinum(self):
        o = make_outlet(monthly_revenue=60_000, brand_revenue=4_000, yoy_growth=20, is_key_account=True, linked_hcp=10)
        result = self.engine.segment(o)
        assert result.tier in (OutletTier.PLATINUM, OutletTier.GOLD)

    def test_low_value_outlet_bronze_or_silver(self):
        o = make_outlet(monthly_revenue=2_000, brand_revenue=50, yoy_growth=1, throughput=20, linked_hcp=0)
        result = self.engine.segment(o)
        assert result.tier in (OutletTier.BRONZE, OutletTier.SILVER)

    def test_score_0_to_100(self):
        for monthly in [1_000, 10_000, 50_000, 100_000]:
            o = make_outlet(monthly_revenue=monthly, brand_revenue=min(monthly, 500))
            result = self.engine.segment(o)
            assert 0 <= result.composite_score <= 100

    def test_visit_frequency_matches_tier(self):
        o = make_outlet(monthly_revenue=60_000, brand_revenue=4_000, yoy_growth=20, is_key_account=True)
        result = self.engine.segment(o)
        assert result.recommended_visits_per_month == VISIT_FREQUENCY[result.tier]

    def test_promo_multiplier_matches_tier(self):
        o = make_outlet()
        result = self.engine.segment(o)
        assert result.promo_budget_multiplier == PROMO_MULTIPLIER[result.tier]

    def test_whitespace_detection(self):
        # High revenue, low brand share → whitespace
        o = make_outlet(monthly_revenue=50_000, brand_revenue=100)  # brand share 0.2%
        result = self.engine.segment(o)
        assert result.is_whitespace is True

    def test_no_whitespace_high_penetration(self):
        # High revenue, high brand share → not whitespace
        o = make_outlet(monthly_revenue=20_000, brand_revenue=5_000)  # 25% brand share
        result = self.engine.segment(o)
        assert result.is_whitespace is False

    def test_tier_change_new(self):
        o = make_outlet(current_tier=None)
        result = self.engine.segment(o)
        assert result.tier_change == "NEW"

    def test_tier_change_up(self):
        o = make_outlet(monthly_revenue=80_000, brand_revenue=5_000, yoy_growth=25, is_key_account=True, current_tier="BRONZE")
        result = self.engine.segment(o)
        assert result.tier_change == "UP"

    def test_segment_portfolio_sorted(self):
        outlets = [make_outlet(f"P{i}", monthly_revenue=5_000*i+1_000) for i in range(1, 5)]
        results = self.engine.segment_portfolio(outlets)
        scores = [r.composite_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_segment_portfolio_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.engine.segment_portfolio([])

    def test_portfolio_summary_keys(self):
        outlets = [make_outlet(f"O{i}") for i in range(3)]
        results = self.engine.segment_portfolio(outlets)
        summary = self.engine.portfolio_summary(results)
        assert "tier_distribution" in summary
        assert "whitespace_outlets" in summary
        assert summary["total_outlets"] == 3

    def test_invalid_outlet_type_raises(self):
        with pytest.raises(TypeError):
            self.engine.segment({"outlet_id": "bad"})

    def test_invalid_weights_raises(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            OutletSegmentationEngine(weights={"a": 0.5, "b": 0.3})
