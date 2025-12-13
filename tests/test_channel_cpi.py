"""
Unit tests for Channel Performance Index and growth rate methods.
"""
import pytest
import pandas as pd
from src.main import PharmacyChannelAnalytics


@pytest.fixture
def analyzer():
    return PharmacyChannelAnalytics()


@pytest.fixture
def channel_df():
    return pd.DataFrame({
        "channel": ["Hospital", "Retail", "Retail", "Hospital",
                    "Online", "Online"],
        "sales_value": [500000, 200000, 220000, 480000, 80000, 90000],
        "sales_target": [450000, 180000, 200000, 500000, 100000, 100000],
        "channel_cost":  [50000, 30000, 30000, 50000, 10000, 10000],
    })


class TestChannelPerformanceIndex:

    def test_returns_one_row_per_channel(self, analyzer, channel_df):
        result = analyzer.calculate_channel_performance_index(channel_df)
        assert len(result) == 3  # Hospital, Retail, Online

    def test_cpi_score_0_to_100(self, analyzer, channel_df):
        result = analyzer.calculate_channel_performance_index(channel_df)
        assert (result["cpi_score"] >= 0).all()
        assert (result["cpi_score"] <= 100).all()

    def test_cpi_band_values(self, analyzer, channel_df):
        valid_bands = {"Excellent", "Good", "Fair", "Underperforming"}
        result = analyzer.calculate_channel_performance_index(channel_df)
        for band in result["cpi_band"]:
            assert band in valid_bands

    def test_sorted_descending_by_cpi(self, analyzer, channel_df):
        result = analyzer.calculate_channel_performance_index(channel_df)
        scores = result["cpi_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_empty_dataframe_raises(self, analyzer):
        with pytest.raises(ValueError, match="DataFrame cannot be empty"):
            analyzer.calculate_channel_performance_index(pd.DataFrame())

    def test_missing_channel_col_raises(self, analyzer, channel_df):
        with pytest.raises(ValueError, match="not found in DataFrame"):
            analyzer.calculate_channel_performance_index(
                channel_df, channel_col="nonexistent"
            )

    def test_no_target_still_works(self, analyzer, channel_df):
        df_no_target = channel_df.drop(columns=["sales_target"])
        result = analyzer.calculate_channel_performance_index(df_no_target)
        assert len(result) == 3
        assert "target_attainment_pct" not in result.columns


class TestChannelGrowthRates:

    def test_growth_rate_calculated(self, analyzer):
        df = pd.DataFrame({
            "channel": ["Retail"] * 3 + ["Hospital"] * 3,
            "period": ["Q1", "Q2", "Q3"] * 2,
            "sales_value": [100000, 120000, 110000, 200000, 210000, 190000],
        })
        result = analyzer.get_channel_growth_rates(df)
        # Q2 Retail: (120k-100k)/100k = 20%
        q2_retail = result[(result["channel"] == "Retail") & (result["period"] == "Q2")]
        assert not q2_retail.empty
        assert q2_retail.iloc[0]["growth_rate_pct"] == pytest.approx(20.0, abs=0.1)

    def test_base_period_trend(self, analyzer):
        df = pd.DataFrame({
            "channel": ["Retail", "Retail"],
            "period": ["Q1", "Q2"],
            "sales_value": [100000, 120000],
        })
        result = analyzer.get_channel_growth_rates(df)
        q1 = result[result["period"] == "Q1"].iloc[0]
        assert q1["growth_trend"] == "base_period"

    def test_empty_raises(self, analyzer):
        with pytest.raises(ValueError, match="DataFrame cannot be empty"):
            analyzer.get_channel_growth_rates(pd.DataFrame())
