# Changelog - Pharmacy Channel Analytics

All notable changes to this project are documented in this file. The
format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.8.0] - 2026-04-20

### Added
- **Channel Concentration Analyzer** (`src/channel_concentration_analyzer.py`)
  — portfolio-level concentration and Pareto analytics for pharmacy
  distribution:
  - Outlet-level Herfindahl-Hirschman Index (HHI) on the 0-10,000 scale
    with DOJ/FTC concentration bands (unconcentrated / moderate / high).
  - Scale-free normalised HHI (HHI*) for cross-portfolio comparison.
  - Effective-number-of-outlets (1 / HHI fraction).
  - Pareto 80/20 ranking with configurable cutoff.
  - Retail-vs-hospital-vs-institutional channel split with within-channel
    HHI and dominant-channel detection.
  - Immutable dataclass results (`ConcentrationResult`, `ParetoResult`,
    `ChannelSplitResult`) — inputs are never mutated.
  - Google-style docstrings on every public method.
- **Sample dataset** — `demo/sample_data.csv` with 18 Indonesian pharma
  outlet-month rows spanning Apotek Kimia Farma, Apotek K-24, Guardian,
  RS Siloam, RSUD, and Dinas Kesehatan across six cities.
- **Demo script** — `demo/run_concentration_demo.py` renders an HHI /
  Pareto / channel-split dashboard for the sample dataset.
- **Tests** — 22 new tests in `tests/test_channel_concentration_analyzer.py`
  covering equal-share HHI, monopoly HHI, band thresholds, Pareto 80/20,
  channel split, immutability, and edge cases (zero sales, NaN revenue,
  duplicate outlet IDs, missing channel labels, empty DataFrame).
- **Validator tests** — 11 new tests in `tests/test_validators.py`
  exercising missing fields, empty strings, negative numbers, adjustment
  allowances, duplicate rows, and empty DataFrames.

### Changed
- `README.md` — added concentration feature, quickstart for
  `demo/sample_data.csv`, column schema, and example concentration output.
- Test badge bumped from 132 to 165 passing tests.

## [1.7.1] - 2026-03-28

### Added
- Edge case validators and handlers.
- Additional unit tests across the analyzer surface.
- Realistic sample data (`sample_data/realistic_data.csv`).
- README validation examples.

## [1.7.0] - 2026-03-26

### Added
- **OutletSegmentationEngine** (`src/outlet_segmentation_engine.py`) — multi-dimensional pharmacy tier segmentation
  - PLATINUM / GOLD / SILVER / BRONZE tier assignment via weighted composite score (0–100)
  - Four scoring dimensions: sales potential (40%), strategic importance (25%), relationship quality (20%), operational efficiency (15%)
  - Customisable dimension weights with validation (must sum to 1.0)
  - Recommended visit frequency by tier: 4 / 2 / 1 / 0 visits/month
  - Promotional budget multiplier by tier: 3.0× / 1.8× / 1.0× / 0.4×
  - Whitespace detection: high-potential outlets with low brand penetration
  - Tier migration tracking: NEW / UP / DOWN / STABLE vs previous assignment
  - Action item generation: in-stock alerts, whitespace activation, distributor routing
  - Portfolio segmentation with composite-score ranking and portfolio summary
- Unit tests: 14 new tests in `tests/test_outlet_segmentation_engine.py`

## [1.6.0] - 2026-03-25

### Added
- **Channel ROI Analyzer** (`src/channel_roi_analyzer.py`) — investment return analysis across pharma distribution channels
  - Gross profit, gross margin %, and contribution margin per channel
  - ROI % computed as (gross profit − investment) / investment × 100
  - Revenue-per-investment ratio and cost-per-unit-sold
  - Incremental units vs baseline and cost-per-incremental-unit (CPIU)
  - Break-even volume calculation from unit contribution margin
  - ROI grading: A (>200%), B (100–200%), C (50–100%), D (<50%), F (negative)
  - Automated flags: low margin, negative ROI, high channel fees, CPIU > ASP, zero sales
  - Portfolio batch analysis with ROI-grade-based ranking
  - Portfolio summary with best/worst channel and grade distribution
- Unit tests: 17 new tests in `tests/test_channel_roi_analyzer.py`

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
