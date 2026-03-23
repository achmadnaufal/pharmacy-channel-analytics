"""Unit tests for MarketShareTracker."""
import pytest
from src.market_share_tracker import MarketShareTracker


@pytest.fixture
def tracker():
    t = MarketShareTracker(market_name="Antidiabetic - Oral")
    # Q1 2025
    t.record_sales("Metformin", "Retail", "2025-Q1", units=15200, value_usd=18240)
    t.record_sales("Sitagliptin", "Retail", "2025-Q1", units=8400, value_usd=84000)
    t.record_sales("Empagliflozin", "Retail", "2025-Q1", units=3200, value_usd=64000)
    t.record_sales("Metformin", "Hospital", "2025-Q1", units=5100, value_usd=6120)
    t.record_sales("Sitagliptin", "Hospital", "2025-Q1", units=2200, value_usd=22000)
    # Q2 2025
    t.record_sales("Metformin", "Retail", "2025-Q2", units=16100, value_usd=19320)
    t.record_sales("Sitagliptin", "Retail", "2025-Q2", units=8800, value_usd=88000)
    t.record_sales("Empagliflozin", "Retail", "2025-Q2", units=4100, value_usd=82000)
    t.record_sales("Metformin", "Hospital", "2025-Q2", units=5400, value_usd=6480)
    t.record_sales("Sitagliptin", "Hospital", "2025-Q2", units=2400, value_usd=24000)
    return t


# --- Input validation ---

def test_negative_units_raises():
    t = MarketShareTracker()
    with pytest.raises(ValueError, match="units"):
        t.record_sales("DrugA", "Retail", "2025-Q1", units=-10)

def test_negative_value_raises():
    t = MarketShareTracker()
    with pytest.raises(ValueError, match="value_usd"):
        t.record_sales("DrugA", "Retail", "2025-Q1", units=100, value_usd=-50)

def test_empty_brand_raises():
    t = MarketShareTracker()
    with pytest.raises(ValueError, match="brand"):
        t.record_sales("", "Retail", "2025-Q1", units=100)

def test_empty_period_raises():
    t = MarketShareTracker()
    with pytest.raises(ValueError, match="period"):
        t.record_sales("DrugA", "Retail", "", units=100)


# --- Counts ---

def test_len(tracker):
    assert len(tracker) == 10

def test_periods(tracker):
    assert tracker.periods() == ["2025-Q1", "2025-Q2"]

def test_brands(tracker):
    brands = tracker.brands()
    assert "Metformin" in brands
    assert "Sitagliptin" in brands

def test_channels(tracker):
    assert set(tracker.channels()) == {"Retail", "Hospital"}


# --- Market share by period ---

def test_share_sums_to_100_retail(tracker):
    shares = tracker.market_share_by_period(channel="Retail")
    for period, brands in shares.items():
        total = sum(brands.values())
        assert abs(total - 100.0) < 0.1, f"{period}: {total}"

def test_share_sums_to_100_all_channels(tracker):
    shares = tracker.market_share_by_period()
    for period, brands in shares.items():
        total = sum(brands.values())
        assert abs(total - 100.0) < 0.1

def test_metformin_leads_retail_by_units(tracker):
    shares = tracker.market_share_by_period(channel="Retail")
    q1_brands = shares["2025-Q1"]
    assert q1_brands["Metformin"] > q1_brands["Sitagliptin"]

def test_value_share_empagliflozin_higher_than_units(tracker):
    unit_shares = tracker.market_share_by_period(channel="Retail", metric="units")
    value_shares = tracker.market_share_by_period(channel="Retail", metric="value_usd")
    # Empagliflozin is premium priced → higher value share than unit share
    assert value_shares["2025-Q1"]["Empagliflozin"] > unit_shares["2025-Q1"]["Empagliflozin"]

def test_invalid_metric_raises(tracker):
    with pytest.raises(ValueError, match="metric"):
        tracker.market_share_by_period(metric="revenue")


# --- Share trend ---

def test_trend_metformin_has_direction(tracker):
    trend = tracker.share_trend("Metformin", channel="Retail")
    # Metformin has a valid trend direction (rising/falling/stable)
    assert trend["trend_direction"] in ("rising", "falling", "stable")

def test_trend_has_required_keys(tracker):
    trend = tracker.share_trend("Sitagliptin")
    for key in ["brand", "periods", "shares", "avg_share_pct", "trend_direction", "delta_pp"]:
        assert key in trend

def test_trend_unknown_brand(tracker):
    trend = tracker.share_trend("UnknownDrug")
    assert all(s == 0.0 for s in trend["shares"])

def test_trend_periods_aligned(tracker):
    trend = tracker.share_trend("Metformin", channel="Retail")
    assert len(trend["periods"]) == len(trend["shares"])


# --- Top brands ---

def test_top_brands_length(tracker):
    top = tracker.top_brands("2025-Q1", channel="Retail", top_n=2)
    assert len(top) == 2

def test_top_brands_sorted(tracker):
    top = tracker.top_brands("2025-Q1", channel="Retail")
    shares = [s for _, s in top]
    assert shares == sorted(shares, reverse=True)

def test_top_brands_unknown_period(tracker):
    with pytest.raises(KeyError):
        tracker.top_brands("2030-Q4")


# --- Competitive landscape ---

def test_competitive_landscape_leader(tracker):
    landscape = tracker.competitive_landscape("2025-Q1", channel="Retail")
    assert landscape["leader"] == "Metformin"

def test_competitive_landscape_hhi(tracker):
    landscape = tracker.competitive_landscape("2025-Q1", channel="Retail")
    assert 0 < landscape["herfindahl_index"] <= 10000

def test_competitive_landscape_top3_le_100(tracker):
    landscape = tracker.competitive_landscape("2025-Q1", channel="Retail")
    assert landscape["top_3_combined_pct"] <= 100.0

def test_competitive_landscape_unknown_period(tracker):
    with pytest.raises(KeyError):
        tracker.competitive_landscape("2030-Q1")


# --- Bulk record ---

def test_bulk_record():
    t = MarketShareTracker()
    rows = [
        {"brand": "DrugA", "channel": "Retail", "period": "2025-Q1", "units": 100},
        {"brand": "DrugB", "channel": "Retail", "period": "2025-Q1", "units": 200},
    ]
    n = t.record_bulk(rows)
    assert n == 2
    assert len(t) == 2


# --- Repr ---

def test_repr(tracker):
    assert "MarketShareTracker" in repr(tracker)
    assert "Antidiabetic" in repr(tracker)
