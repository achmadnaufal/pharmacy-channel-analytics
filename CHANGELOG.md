# Changelog - Pharmacy Channel Analytics

## [1.5.0] - 2026-03-23

### Added
- `src/market_share_tracker.py` — Drug market share tracking across channels and periods
  - `MarketShareTracker` with unit and value-based share calculation
  - `market_share_by_period()` — brand share % per period with channel filter
  - `share_trend()` — per-brand trend with delta pp and direction classification
  - `top_brands()` — ranked brands for a given period/channel
  - `competitive_landscape()` — HHI concentration index and top-3 combined share
  - `record_bulk()` — batch sales recording
- `data/sample_market_share_data.csv` — 22 records across antidiabetic and oncology markets
- 26 unit tests in `tests/test_market_share_tracker.py`

## [1.4.0] - 2026-03-22

### Added
- **Seasonal Demand Adjuster** (`src/seasonal_demand_adjuster.py`) — classical decomposition for pharmacy channel sales
  - Monthly data decomposition into trend (centred moving average), seasonal indices, adjusted sales, and irregular component
  - `MonthlyChannelData` dataclass with period, channel, sales, and optional brand fields
  - `SeasonalAdjustmentResult` dataclass with full component series and peak/trough identification
  - `adjust()` — channel-specific decomposition with brand filter and sorted period output
  - `compare_channels()` — batch decomposition across multiple channels (silently skips insufficient-data channels)
  - `seasonal_index_summary()` — collapses multi-year SI values to a 12-month annual pattern (Jan–Dec)
  - Seasonal indices normalised to average 1.0 across all months
  - Duplicate period detection and validation
  - Configurable CMA window (default 12 for monthly/annual seasonality) and minimum data threshold
- **Unit tests** — 22 tests in `tests/test_seasonal_demand_adjuster.py` covering decomposition quality, edge cases, and filters

### References
- US Census Bureau X-13ARIMA-SEATS documentation
- Holt (1957) Forecasting seasonals and trends by exponentially weighted moving averages
- IQVIA Channel Analytics Seasonal Correction Methodology (2022)

## [1.3.0] - 2026-03-18

### Added
- **Channel Mix Optimiser** (`src/channel_mix_optimizer.py`) — ROI-maximising budget allocation engine
  - `ChannelMetrics` dataclass with ROI, revenue-per-dollar, and strategic-weight-adjusted efficiency scoring
  - `ChannelMixOptimizer`: distributes budget proportionally to efficiency scores with min/max guardrails
  - Diminishing-returns model (square-root revenue curve) for marginal investment projections
  - `optimise()`: channel-by-channel allocation with investment change and projected ROI
  - `portfolio_summary()`: current vs projected portfolio metrics (revenue uplift %, blended ROI)
  - Default strategic weights catalogue for hospital/retail/clinic/e-commerce/specialty channels
- **Unit tests** — 25 tests in `tests/test_channel_mix_optimizer.py` covering edge cases, budget conservation, cap enforcement, and single-channel scenarios

## [1.2.0] - 2026-03-15

### Added
- **Channel Performance Index (CPI)** — `calculate_channel_performance_index()`: Composite 0–100 score per channel weighting sales share (40pt), target attainment (35pt), and ROI (25pt); classifies into Excellent/Good/Fair/Underperforming bands
- **Channel Growth Rate Tracker** — `get_channel_growth_rates()`: Calculates period-over-period growth rates per channel with trend classification (growing/stable/declining)
- **Unit Tests** — 10 new tests in `tests/test_channel_cpi.py` covering CPI scoring, band assignment, sorting, growth calculations, and error handling
- **Sample Data** — Added `sample_data/channel_performance.csv` with representative retail/hospital/online channel data
- **README** — Added CPI and growth rate usage examples

## [1.1.0] - 2026-03-10

### Added

- **Channel Analyzer Module**: New `channel_analyzer.py` with PharmacyChannelAnalyzer
  - `calculate_channel_metrics()`: KPI calculation per channel
  - `calculate_channel_growth()`: Period-over-period growth tracking
  - `channel_mix_analysis()`: Sales distribution across channels
  - `identify_top_products_by_channel()`: Top product analysis
  - `calculate_channel_efficiency()`: Operational efficiency metrics
- **Test Suite**: 5 comprehensive tests for channel analysis
- **Performance Metrics**: Transaction value, unit pricing, efficiency scoring

## [1.0.0] - 2026-01-15

### Added

- Initial pharmacy channel analytics framework
