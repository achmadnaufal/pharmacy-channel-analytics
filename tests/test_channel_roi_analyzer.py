"""Unit tests for ChannelROIAnalyzer."""

import pytest
from src.channel_roi_analyzer import ChannelROIAnalyzer, ChannelInvestmentData


@pytest.fixture
def analyzer():
    return ChannelROIAnalyzer()


def make_data(
    channel_id="HOSP",
    channel_name="Hospital Direct",
    gross_revenue=1_000_000,
    units_sold=5000,
    cogs=400_000,
    fees=50_000,
    logistics=30_000,
    sf_cost=100_000,
    marketing=50_000,
    baseline=4500,
):
    return ChannelInvestmentData(
        channel_id=channel_id,
        channel_name=channel_name,
        gross_revenue=gross_revenue,
        units_sold=units_sold,
        cogs_total=cogs,
        channel_fees=fees,
        logistics_cost=logistics,
        sales_force_cost=sf_cost,
        marketing_spend=marketing,
        baseline_units=baseline,
    )


class TestChannelInvestmentData:
    def test_negative_revenue_raises(self):
        with pytest.raises(ValueError, match="gross_revenue"):
            ChannelInvestmentData("C1", "C", -100, 100, 50, 5, 3, 10, 5)

    def test_negative_units_raises(self):
        with pytest.raises(ValueError, match="units_sold"):
            ChannelInvestmentData("C1", "C", 100, -1, 50, 5, 3, 10, 5)

    def test_total_investment_property(self):
        d = make_data(sf_cost=100_000, marketing=50_000)
        assert d.total_investment == 150_000

    def test_total_cost_of_channel(self):
        d = make_data(cogs=400_000, fees=50_000, logistics=30_000, sf_cost=100_000, marketing=50_000)
        assert d.total_cost_of_channel == 630_000


class TestChannelROIAnalyzer:
    def test_basic_roi_calculation(self, analyzer):
        d = make_data()
        result = analyzer.analyze_channel(d)
        # Gross profit = 1M - 400k - 50k - 30k = 520k
        # ROI = (520k - 150k) / 150k * 100 = 246.7%
        assert result.gross_profit == pytest.approx(520_000, rel=1e-4)
        assert result.roi_pct == pytest.approx(246.67, rel=1e-2)

    def test_roi_grade_a(self, analyzer):
        d = make_data()
        result = analyzer.analyze_channel(d)
        assert result.roi_grade == "A"

    def test_roi_grade_f_negative(self, analyzer):
        d = make_data(gross_revenue=100_000, cogs=90_000, fees=5_000, logistics=5_000, sf_cost=50_000, marketing=20_000)
        result = analyzer.analyze_channel(d)
        assert result.roi_grade == "F"

    def test_gross_margin_pct(self, analyzer):
        d = make_data()
        result = analyzer.analyze_channel(d)
        assert result.gross_margin_pct == pytest.approx(52.0, rel=1e-3)

    def test_incremental_units(self, analyzer):
        d = make_data(units_sold=5000, baseline=4500)
        result = analyzer.analyze_channel(d)
        assert result.incremental_units == 500

    def test_cpiu_calculation(self, analyzer):
        d = make_data(units_sold=5000, baseline=4500, sf_cost=100_000, marketing=50_000)
        result = analyzer.analyze_channel(d)
        # CPIU = 150k / 500 = 300
        assert result.cpiu == pytest.approx(300.0)

    def test_cpiu_none_when_no_increment(self, analyzer):
        d = make_data(units_sold=4500, baseline=4500)
        result = analyzer.analyze_channel(d)
        assert result.cpiu is None

    def test_zero_sales_flag(self, analyzer):
        d = make_data(units_sold=0, gross_revenue=0, baseline=0)
        result = analyzer.analyze_channel(d)
        assert any("ZERO_SALES" in f for f in result.flags)

    def test_low_margin_flag(self, analyzer):
        d = make_data(gross_revenue=100_000, cogs=85_000, fees=3_000, logistics=2_000)
        result = analyzer.analyze_channel(d)
        assert any("LOW_MARGIN" in f for f in result.flags)

    def test_to_dict_keys(self, analyzer):
        d = make_data()
        result = analyzer.analyze_channel(d)
        dct = result.to_dict()
        assert "roi_pct" in dct
        assert "roi_grade" in dct
        assert "cpiu" in dct
        assert "break_even_units" in dct

    def test_analyze_portfolio_sorted(self, analyzer):
        channels = [
            make_data("LOW", gross_revenue=100_000, cogs=90_000, fees=5_000, logistics=5_000, sf_cost=50_000, marketing=20_000),
            make_data("HIGH", gross_revenue=1_000_000, cogs=400_000, fees=50_000, logistics=30_000, sf_cost=100_000, marketing=50_000),
        ]
        results = analyzer.analyze_portfolio(channels)
        # High ROI channel should come first
        assert results[0].channel_id == "HIGH"

    def test_portfolio_summary(self, analyzer):
        channels = [make_data("C1"), make_data("C2", channel_id="C2", channel_name="Retail", gross_revenue=500_000, units_sold=2500, cogs=200_000, fees=25_000, logistics=15_000, sf_cost=50_000, marketing=25_000)]
        results = analyzer.analyze_portfolio(channels)
        summary = analyzer.portfolio_summary(results)
        assert summary["total_channels"] == 2
        assert "portfolio_roi_pct" in summary
        assert "best_channel" in summary

    def test_empty_portfolio_summary(self, analyzer):
        summary = analyzer.portfolio_summary([])
        assert summary["total_channels"] == 0

    def test_zero_investment_roi(self, analyzer):
        d = make_data(sf_cost=0, marketing=0)
        result = analyzer.analyze_channel(d)
        assert result.roi_pct == float("inf") or result.roi_pct > 0

    def test_custom_asp(self):
        analyzer_asp = ChannelROIAnalyzer(avg_selling_price=200.0)
        d = make_data()
        result = analyzer_asp.analyze_channel(d)
        assert result.break_even_units >= 0

    def test_invalid_asp_raises(self):
        with pytest.raises(ValueError, match="avg_selling_price"):
            ChannelROIAnalyzer(avg_selling_price=-10)
