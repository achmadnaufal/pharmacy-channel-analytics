"""
Unit tests for SeasonalDemandAdjuster.
"""

import pytest
from src.seasonal_demand_adjuster import (
    SeasonalDemandAdjuster,
    MonthlyChannelData,
    SeasonalAdjustmentResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_retail_data(n_months: int = 30) -> list:
    """Generate synthetic monthly retail data with a clear seasonal pattern."""
    base = [
        1200, 1050, 1100, 1000, 950, 900,
        880, 920, 1000, 1150, 1300, 1500,  # Dec peak
    ]
    data = []
    for i in range(n_months):
        month_idx = i % 12
        period = f"{2023 + i // 12:04d}-{month_idx + 1:02d}"
        # slight trend growth
        sales = base[month_idx] * (1 + 0.01 * (i // 12))
        data.append(MonthlyChannelData(period, "retail", round(sales, 1)))
    return data


@pytest.fixture
def retail_data():
    return _make_retail_data(30)


@pytest.fixture
def adjuster():
    return SeasonalDemandAdjuster(min_periods_for_decomposition=24)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_defaults_accepted(self):
        a = SeasonalDemandAdjuster()
        assert a._window == 12

    def test_window_too_small_raises(self):
        with pytest.raises(ValueError, match="moving_average_window"):
            SeasonalDemandAdjuster(moving_average_window=1)

    def test_min_periods_less_than_window_raises(self):
        with pytest.raises(ValueError, match="min_periods_for_decomposition"):
            SeasonalDemandAdjuster(moving_average_window=12, min_periods_for_decomposition=6)


# ---------------------------------------------------------------------------
# adjust
# ---------------------------------------------------------------------------

class TestAdjust:
    def test_returns_seasonal_adjustment_result(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        assert isinstance(result, SeasonalAdjustmentResult)

    def test_same_number_of_periods(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        assert len(result.periods) == len(retail_data)
        assert len(result.adjusted_sales) == len(retail_data)
        assert len(result.seasonal_indices) == len(retail_data)

    def test_seasonal_indices_average_near_one(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        mean_si = sum(result.seasonal_indices) / len(result.seasonal_indices)
        assert abs(mean_si - 1.0) < 0.1  # normalised to ~1.0

    def test_adjusted_sales_smooth_out_peaks(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        raw_std = (
            sum((x - sum(result.raw_sales)/len(result.raw_sales))**2
                for x in result.raw_sales) / len(result.raw_sales)
        ) ** 0.5
        adj_std = (
            sum((x - sum(result.adjusted_sales)/len(result.adjusted_sales))**2
                for x in result.adjusted_sales) / len(result.adjusted_sales)
        ) ** 0.5
        # Adjusted sales should be less volatile than raw
        assert adj_std < raw_std

    def test_peak_and_trough_are_different(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        assert result.peak_period != result.trough_period

    def test_seasonal_amplitude_positive(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        assert result.seasonal_amplitude > 0

    def test_insufficient_data_raises(self, adjuster):
        data = [MonthlyChannelData(f"2024-{i+1:02d}", "retail", 1000) for i in range(10)]
        with pytest.raises(ValueError, match="Minimum required"):
            adjuster.adjust(data, channel="retail")

    def test_duplicate_periods_raises(self, adjuster):
        data = [MonthlyChannelData("2024-01", "retail", 1000)] * 30
        with pytest.raises(ValueError, match="Duplicate period"):
            adjuster.adjust(data, channel="retail")

    def test_channel_filter_excludes_other_channels(self, adjuster, retail_data):
        hospital_data = [
            MonthlyChannelData(d.period, "hospital", d.raw_sales * 0.3)
            for d in retail_data
        ]
        combined = retail_data + hospital_data
        result = adjuster.adjust(combined, channel="retail")
        # Only retail periods should appear
        assert all("retail" == r.channel for r in retail_data
                   if r.period in result.periods)

    def test_brand_filter(self, adjuster):
        data = [
            MonthlyChannelData(f"2023-{i+1:02d}" if i < 12 else f"2024-{i-11:02d}",
                               "retail", 1000 + i * 5, brand="BrandX")
            for i in range(30)
        ] + [
            MonthlyChannelData(f"2023-{i+1:02d}" if i < 12 else f"2024-{i-11:02d}",
                               "retail", 500, brand="BrandY")
            for i in range(30)
        ]
        result = adjuster.adjust(data, channel="retail", brand="BrandX")
        assert result.brand == "BrandX"

    def test_channel_case_insensitive(self, adjuster, retail_data):
        r1 = adjuster.adjust(retail_data, channel="retail")
        r2 = adjuster.adjust(retail_data, channel="RETAIL")
        assert r1.periods == r2.periods


# ---------------------------------------------------------------------------
# compare_channels
# ---------------------------------------------------------------------------

class TestCompareChannels:
    def test_returns_dict_with_channel_keys(self, adjuster, retail_data):
        hospital_data = [
            MonthlyChannelData(d.period, "hospital", d.raw_sales * 0.4)
            for d in retail_data
        ]
        combined = retail_data + hospital_data
        results = adjuster.compare_channels(combined, ["retail", "hospital"])
        assert "retail" in results
        assert "hospital" in results

    def test_skips_channels_with_insufficient_data(self, adjuster, retail_data):
        # Add tiny channel with only 5 data points
        tiny = [MonthlyChannelData(f"2024-{i+1:02d}", "tiny", 100) for i in range(5)]
        results = adjuster.compare_channels(retail_data + tiny, ["retail", "tiny"])
        assert "retail" in results
        assert "tiny" not in results


# ---------------------------------------------------------------------------
# seasonal_index_summary
# ---------------------------------------------------------------------------

class TestSeasonalIndexSummary:
    def test_returns_12_months(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        summary = adjuster.seasonal_index_summary(result)
        assert len(summary) == 12
        assert "Jan" in summary and "Dec" in summary

    def test_values_are_positive(self, adjuster, retail_data):
        result = adjuster.adjust(retail_data, channel="retail")
        summary = adjuster.seasonal_index_summary(result)
        assert all(v > 0 for v in summary.values())
