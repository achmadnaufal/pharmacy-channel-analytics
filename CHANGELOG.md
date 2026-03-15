# Changelog - Pharmacy Channel Analytics

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
