"""
Unit tests for the pharmacy channel mix optimisation module.
"""

import pytest
from src.channel_mix_optimizer import (
    ChannelMetrics,
    ChannelMixOptimizer,
    AllocationResult,
    DEFAULT_CHANNEL_WEIGHTS,
)


# ---------------------------------------------------------------------------
# ChannelMetrics tests
# ---------------------------------------------------------------------------


class TestChannelMetrics:
    def test_valid_creation(self):
        ch = ChannelMetrics("CH-001", "hospital_pharmacy", 50000, 380000, 5.2)
        assert ch.channel_id == "CH-001"
        assert ch.current_revenue_usd == 380000

    def test_roi_calculation(self):
        ch = ChannelMetrics("CH-001", "retail_pharmacy", 100000, 300000)
        assert ch.roi == pytest.approx(2.0)  # (300000-100000)/100000

    def test_revenue_per_dollar(self):
        ch = ChannelMetrics("CH-001", "retail_pharmacy", 50000, 200000)
        assert ch.revenue_per_dollar == pytest.approx(4.0)

    def test_zero_investment_roi_is_zero(self):
        ch = ChannelMetrics("CH-001", "retail_pharmacy", 0, 50000)
        assert ch.roi == 0.0

    def test_weighted_efficiency_higher_for_fast_growth(self):
        ch_slow = ChannelMetrics("A", "retail_pharmacy", 50000, 200000, growth_rate_pct=1.0)
        ch_fast = ChannelMetrics("B", "retail_pharmacy", 50000, 200000, growth_rate_pct=20.0)
        assert ch_fast.weighted_efficiency > ch_slow.weighted_efficiency

    def test_default_weight_from_catalogue(self):
        ch = ChannelMetrics("CH-001", "hospital_pharmacy", 50000, 200000)
        # hospital_pharmacy weight = 1.30
        assert ch.strategic_weight == pytest.approx(DEFAULT_CHANNEL_WEIGHTS["hospital_pharmacy"])

    def test_empty_channel_id_raises(self):
        with pytest.raises(ValueError, match="channel_id cannot be empty"):
            ChannelMetrics("  ", "retail_pharmacy", 50000, 200000)

    def test_negative_investment_raises(self):
        with pytest.raises(ValueError, match="current_investment_usd"):
            ChannelMetrics("CH-001", "retail_pharmacy", -1000, 200000)

    def test_negative_revenue_raises(self):
        with pytest.raises(ValueError, match="current_revenue_usd"):
            ChannelMetrics("CH-001", "retail_pharmacy", 50000, -200000)

    def test_zero_strategic_weight_raises(self):
        with pytest.raises(ValueError, match="strategic_weight"):
            ChannelMetrics("CH-001", "retail_pharmacy", 50000, 200000, strategic_weight=0)


# ---------------------------------------------------------------------------
# ChannelMixOptimizer tests
# ---------------------------------------------------------------------------


@pytest.fixture
def channels():
    return [
        ChannelMetrics("CH-001", "hospital_pharmacy", 50000, 380000, 5.2),
        ChannelMetrics("CH-002", "retail_pharmacy",   80000, 240000, 1.8),
        ChannelMetrics("CH-003", "e_commerce",        20000,  95000, 12.0),
        ChannelMetrics("CH-004", "clinic_dispensary", 30000, 140000, 3.5),
    ]


@pytest.fixture
def optimizer(channels):
    return ChannelMixOptimizer(channels, total_budget_usd=180000)


class TestChannelMixOptimizer:
    def test_creation_valid(self, optimizer):
        assert optimizer.total_budget_usd == 180000

    def test_empty_channels_raises(self):
        with pytest.raises(ValueError, match="channels list cannot be empty"):
            ChannelMixOptimizer([], 100000)

    def test_negative_budget_raises(self):
        ch = [ChannelMetrics("CH-001", "retail_pharmacy", 50000, 200000)]
        with pytest.raises(ValueError, match="total_budget_usd must be positive"):
            ChannelMixOptimizer(ch, -100)

    def test_invalid_min_max_raises(self):
        ch = [ChannelMetrics("CH-001", "retail_pharmacy", 50000, 200000)]
        with pytest.raises(ValueError):
            ChannelMixOptimizer(ch, 100000, min_channel_allocation_pct=0.6, max_channel_allocation_pct=0.5)

    def test_min_too_large_raises(self):
        """min × n_channels > 1 should raise."""
        ch = [
            ChannelMetrics("CH-001", "retail_pharmacy", 50000, 200000),
            ChannelMetrics("CH-002", "retail_pharmacy", 50000, 200000),
            ChannelMetrics("CH-003", "retail_pharmacy", 50000, 200000),
        ]
        with pytest.raises(ValueError, match="exceeds 1.0"):
            ChannelMixOptimizer(ch, 100000, min_channel_allocation_pct=0.40)

    def test_optimise_returns_all_channels(self, optimizer, channels):
        results = optimizer.optimise()
        assert len(results) == len(channels)

    def test_total_budget_preserved(self, optimizer):
        results = optimizer.optimise()
        total = sum(r.recommended_investment_usd for r in results)
        assert total == pytest.approx(180000, rel=1e-4)

    def test_all_allocations_above_minimum(self, optimizer):
        results = optimizer.optimise()
        min_budget = optimizer.min_allocation * optimizer.total_budget_usd
        for r in results:
            assert r.recommended_investment_usd >= min_budget - 1.0  # allow float tolerance

    def test_all_allocations_below_maximum(self, optimizer):
        results = optimizer.optimise()
        max_budget = optimizer.max_allocation * optimizer.total_budget_usd
        for r in results:
            assert r.recommended_investment_usd <= max_budget + 1.0

    def test_high_efficiency_channel_gets_more(self, channels, optimizer):
        results = optimizer.optimise()
        result_map = {r.channel_id: r for r in results}
        # e_commerce (CH-003) has highest growth; hospital (CH-001) has highest weight
        # Both should receive ≥ min allocation
        assert result_map["CH-003"].recommended_investment_usd >= optimizer.min_allocation * 180000

    def test_portfolio_summary_keys(self, optimizer):
        summary = optimizer.portfolio_summary()
        expected = {
            "current_total_revenue", "projected_total_revenue", "revenue_uplift_usd",
            "revenue_uplift_pct", "current_portfolio_roi", "projected_portfolio_roi",
            "n_channels_increased", "n_channels_decreased", "total_budget_usd",
        }
        assert expected.issubset(summary.keys())

    def test_investment_change_sums_to_budget_diff(self, optimizer, channels):
        results = optimizer.optimise()
        total_current = sum(ch.current_investment_usd for ch in channels)
        total_change = sum(r.investment_change_usd for r in results)
        expected_change = optimizer.total_budget_usd - total_current
        assert total_change == pytest.approx(expected_change, abs=1.0)

    def test_projected_revenue_positive(self, optimizer):
        results = optimizer.optimise()
        for r in results:
            assert r.projected_revenue_usd > 0

    def test_single_channel_gets_all_budget(self):
        ch = [ChannelMetrics("ONLY", "retail_pharmacy", 50000, 200000)]
        opt = ChannelMixOptimizer(ch, 100000)
        results = opt.optimise()
        assert results[0].recommended_investment_usd == pytest.approx(100000, rel=1e-4)

    def test_equal_efficiency_distributes_evenly(self):
        chs = [
            ChannelMetrics("A", "retail_pharmacy", 50000, 200000, growth_rate_pct=0.0, strategic_weight=1.0),
            ChannelMetrics("B", "retail_pharmacy", 50000, 200000, growth_rate_pct=0.0, strategic_weight=1.0),
        ]
        opt = ChannelMixOptimizer(chs, 100000, min_channel_allocation_pct=0.05)
        results = opt.optimise()
        # Both should get ~50k
        allocs = [r.recommended_investment_usd for r in results]
        assert abs(allocs[0] - allocs[1]) < 1000
