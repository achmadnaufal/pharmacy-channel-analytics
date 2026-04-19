"""Tests for :mod:`src.channel_concentration_analyzer`.

Covers concentration metrics with known values, Pareto 80-20 ranking,
channel split, and edge cases: zero-sales outlets, missing channel
labels, duplicate outlet ids, NaN revenue, and empty DataFrames.
"""
import numpy as np
import pandas as pd
import pytest

from src.channel_concentration_analyzer import (
    ChannelConcentrationAnalyzer,
    ChannelSplitResult,
    ConcentrationResult,
    ParetoResult,
)


@pytest.fixture
def analyzer() -> ChannelConcentrationAnalyzer:
    return ChannelConcentrationAnalyzer()


@pytest.fixture
def portfolio_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "outlet_id": ["A", "B", "C", "D"],
            "channel_type": ["retail", "retail", "hospital", "hospital"],
            "revenue": [4000, 3000, 2000, 1000],
            "units_sold": [40, 30, 20, 10],
        }
    )


@pytest.fixture
def demo_df() -> pd.DataFrame:
    return pd.read_csv("demo/sample_data.csv")


class TestComputeHHI:
    """Concentration metrics with known expected values."""

    def test_equal_shares_give_minimum_hhi(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame(
            {"outlet_id": list("ABCD"), "revenue": [1000, 1000, 1000, 1000]}
        )
        result = analyzer.compute_hhi(df)
        # 4 equal outlets: HHI = 4 * (0.25)^2 * 10000 = 2500
        assert result.hhi == pytest.approx(2500.0, abs=0.01)
        assert result.hhi_normalised == pytest.approx(0.0, abs=1e-6)
        assert result.effective_outlets == pytest.approx(4.0, abs=0.01)
        assert result.outlet_count == 4
        assert result.zero_sales_outlets == 0

    def test_monopoly_gives_max_hhi(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame({"outlet_id": ["A"], "revenue": [5000]})
        result = analyzer.compute_hhi(df)
        assert result.hhi == pytest.approx(10_000.0, abs=0.01)
        assert result.hhi_normalised == pytest.approx(1.0, abs=1e-6)
        assert result.effective_outlets == pytest.approx(1.0, abs=0.01)
        assert result.top_outlet_share == pytest.approx(1.0, abs=1e-6)
        assert result.band == "high"

    def test_known_uneven_hhi(
        self, analyzer: ChannelConcentrationAnalyzer, portfolio_df: pd.DataFrame
    ) -> None:
        # Shares 0.4, 0.3, 0.2, 0.1 => HHI = (0.16+0.09+0.04+0.01)*10000 = 3000
        result = analyzer.compute_hhi(portfolio_df)
        assert result.hhi == pytest.approx(3000.0, abs=0.01)
        assert result.band == "high"
        assert result.top_outlet_share == pytest.approx(0.4, abs=1e-6)

    def test_band_thresholds(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        # 10 equal outlets → HHI = 1000 → unconcentrated
        equal_ten = pd.DataFrame(
            {"outlet_id": [f"O{i}" for i in range(10)], "revenue": [100] * 10}
        )
        assert analyzer.compute_hhi(equal_ten).band == "unconcentrated"

        # 5 equal outlets → HHI = 2000 → moderate
        equal_five = pd.DataFrame(
            {"outlet_id": [f"O{i}" for i in range(5)], "revenue": [100] * 5}
        )
        assert analyzer.compute_hhi(equal_five).band == "moderate"


class TestConcentrationEdgeCases:
    """Edge cases for concentration calculation."""

    def test_empty_dataframe_raises(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        with pytest.raises(ValueError, match="empty"):
            analyzer.compute_hhi(pd.DataFrame())

    def test_non_dataframe_raises(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        with pytest.raises(TypeError):
            analyzer.compute_hhi([{"outlet_id": "A", "revenue": 1}])  # type: ignore[arg-type]

    def test_zero_sales_outlets_counted_not_in_hhi(
        self, analyzer: ChannelConcentrationAnalyzer
    ) -> None:
        df = pd.DataFrame(
            {
                "outlet_id": ["A", "B", "Z1", "Z2"],
                "revenue": [5000, 5000, 0, 0],
            }
        )
        result = analyzer.compute_hhi(df)
        # HHI for 2 equal active outlets = 5000
        assert result.hhi == pytest.approx(5000.0, abs=0.01)
        assert result.outlet_count == 2
        assert result.zero_sales_outlets == 2

    def test_all_zero_sales(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame({"outlet_id": ["A", "B"], "revenue": [0, 0]})
        result = analyzer.compute_hhi(df)
        assert result.hhi == 0.0
        assert result.band == "undefined"
        assert result.outlet_count == 0
        assert result.zero_sales_outlets == 2

    def test_nan_revenue_treated_as_zero(
        self, analyzer: ChannelConcentrationAnalyzer
    ) -> None:
        df = pd.DataFrame(
            {"outlet_id": ["A", "B", "C"], "revenue": [1000, np.nan, 1000]}
        )
        result = analyzer.compute_hhi(df)
        assert result.outlet_count == 2
        assert result.zero_sales_outlets == 1
        assert result.hhi == pytest.approx(5000.0, abs=0.01)

    def test_duplicate_outlet_ids_are_summed(
        self, analyzer: ChannelConcentrationAnalyzer
    ) -> None:
        df = pd.DataFrame(
            {"outlet_id": ["A", "A", "B"], "revenue": [600, 400, 1000]}
        )
        result = analyzer.compute_hhi(df)
        # After dedup: A=1000, B=1000, equal → HHI = 5000
        assert result.outlet_count == 2
        assert result.hhi == pytest.approx(5000.0, abs=0.01)

    def test_missing_column_raises(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame({"outlet_id": ["A"], "rev": [1]})
        with pytest.raises(ValueError, match="revenue"):
            analyzer.compute_hhi(df)

    def test_input_dataframe_not_mutated(
        self, analyzer: ChannelConcentrationAnalyzer, portfolio_df: pd.DataFrame
    ) -> None:
        before = portfolio_df.copy(deep=True)
        analyzer.compute_hhi(portfolio_df)
        pd.testing.assert_frame_equal(portfolio_df, before)


class TestParetoRanking:
    """80-20 ranking behaviour."""

    def test_known_80_20(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame(
            {
                "outlet_id": [f"O{i}" for i in range(10)],
                "revenue": [800, 100, 50, 20, 10, 8, 5, 3, 2, 2],
            }
        )
        result = analyzer.pareto_ranking(df, cutoff=0.8)
        assert isinstance(result, ParetoResult)
        assert result.outlets_to_cutoff == 1
        assert result.share_of_outlets == pytest.approx(0.1, abs=1e-6)
        assert list(result.ranking["rank"]) == list(range(1, 11))
        assert result.ranking.loc[0, "within_cutoff"]
        assert not result.ranking.loc[9, "within_cutoff"]

    def test_equal_shares_pareto(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame(
            {"outlet_id": list("ABCDE"), "revenue": [100, 100, 100, 100, 100]}
        )
        result = analyzer.pareto_ranking(df, cutoff=0.8)
        # Need 4 of 5 to reach 80%
        assert result.outlets_to_cutoff == 4
        assert result.share_of_outlets == pytest.approx(0.8, abs=1e-6)

    def test_invalid_cutoff(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame({"outlet_id": ["A"], "revenue": [1]})
        with pytest.raises(ValueError, match="cutoff"):
            analyzer.pareto_ranking(df, cutoff=0.0)
        with pytest.raises(ValueError, match="cutoff"):
            analyzer.pareto_ranking(df, cutoff=1.5)

    def test_all_zero_revenue(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        df = pd.DataFrame({"outlet_id": ["A", "B"], "revenue": [0, 0]})
        result = analyzer.pareto_ranking(df)
        assert result.outlets_to_cutoff == 0
        assert result.ranking.empty

    def test_empty_dataframe_raises(self, analyzer: ChannelConcentrationAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.pareto_ranking(pd.DataFrame())


class TestChannelSplit:
    """Retail-vs-hospital split with within-channel HHI."""

    def test_basic_split(
        self, analyzer: ChannelConcentrationAnalyzer, portfolio_df: pd.DataFrame
    ) -> None:
        result = analyzer.channel_split(portfolio_df)
        assert isinstance(result, ChannelSplitResult)
        # retail revenue 7000, hospital 3000 → retail dominant
        assert result.dominant_channel == "retail"
        assert result.dominant_share == pytest.approx(0.7, abs=1e-6)
        retail_row = result.per_channel[
            result.per_channel["channel_type"] == "retail"
        ].iloc[0]
        # Within-channel: retail has A=4000, B=3000 → shares 4/7, 3/7
        expected_hhi = ((4 / 7) ** 2 + (3 / 7) ** 2) * 10_000
        assert retail_row["hhi_within_channel"] == pytest.approx(expected_hhi, abs=0.1)

    def test_missing_channel_labels_bucketed_as_unknown(
        self, analyzer: ChannelConcentrationAnalyzer
    ) -> None:
        df = pd.DataFrame(
            {
                "outlet_id": ["A", "B", "C"],
                "channel_type": ["retail", None, "  "],
                "revenue": [100, 200, 300],
                "units_sold": [1, 2, 3],
            }
        )
        result = analyzer.channel_split(df)
        channels = set(result.per_channel["channel_type"])
        assert "Unknown" in channels
        unknown_revenue = (
            result.per_channel.loc[
                result.per_channel["channel_type"] == "Unknown", "revenue"
            ].iloc[0]
        )
        assert unknown_revenue == pytest.approx(500.0, abs=0.01)

    def test_units_sold_optional(
        self, analyzer: ChannelConcentrationAnalyzer
    ) -> None:
        df = pd.DataFrame(
            {
                "outlet_id": ["A", "B"],
                "channel_type": ["retail", "hospital"],
                "revenue": [1000, 500],
            }
        )
        result = analyzer.channel_split(df)
        # Should not raise and units_sold defaults to 0
        assert set(result.per_channel.columns) >= {"revenue", "units_sold"}
        assert (result.per_channel["units_sold"] == 0).all()

    def test_empty_dataframe_raises(
        self, analyzer: ChannelConcentrationAnalyzer
    ) -> None:
        with pytest.raises(ValueError):
            analyzer.channel_split(pd.DataFrame())


class TestSummaryWithDemoData:
    """Sanity checks against the shipped demo CSV."""

    def test_demo_summary_shape(
        self, analyzer: ChannelConcentrationAnalyzer, demo_df: pd.DataFrame
    ) -> None:
        summary = analyzer.summary(demo_df)
        assert set(summary.keys()) == {"concentration", "pareto", "channel_split"}
        assert isinstance(summary["concentration"], ConcentrationResult)
        assert isinstance(summary["pareto"], ParetoResult)
        assert isinstance(summary["channel_split"], ChannelSplitResult)
        # The demo intentionally contains one zero-sales outlet.
        assert summary["concentration"].zero_sales_outlets >= 1
        # All channel labels are present.
        channels = set(summary["channel_split"].per_channel["channel_type"])
        assert {"retail", "hospital", "institutional"}.issubset(channels)
