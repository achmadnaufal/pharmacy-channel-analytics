# Pharmacy Channel Analytics

Retail and hospital pharmacy channel performance analytics

## Features
- Data ingestion from CSV/Excel input files
- Automated analysis and KPI calculation
- Summary statistics and trend reporting
- Sample data generator for testing and development

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from src.main import PharmacyChannelAnalytics

analyzer = PharmacyChannelAnalytics()
df = analyzer.load_data("data/sample.csv")
result = analyzer.analyze(df)
print(result)
```

## Data Format

Expected CSV columns: `pharmacy_id, channel_type, product, month, sales_units, revenue_usd, market_share_pct`

## Project Structure

```
pharmacy-channel-analytics/
├── src/
│   ├── main.py          # Core analysis logic
│   └── data_generator.py # Sample data generator
├── data/                # Data directory (gitignored for real data)
├── examples/            # Usage examples
├── requirements.txt
└── README.md
```

## License

MIT License — free to use, modify, and distribute.


## Usage Examples

### Channel Performance Index

```python
from src.main import PharmacyChannelAnalytics
import pandas as pd

analyzer = PharmacyChannelAnalytics()
df = pd.read_csv("sample_data/channel_performance.csv")

cpi = analyzer.calculate_channel_performance_index(
    df,
    channel_col="channel",
    sales_col="sales_value",
    target_col="sales_target",
    cost_col="channel_cost",
)
print(cpi[["channel", "sales_share_pct", "target_attainment_pct", "roi_pct", "cpi_score", "cpi_band"]])
```

### Channel Growth Rates

```python
growth = analyzer.get_channel_growth_rates(
    df, channel_col="channel", sales_col="sales_value", period_col="period"
)
print(growth[["channel", "period", "sales_value", "growth_rate_pct", "growth_trend"]])
```

Refer to the `tests/` directory for comprehensive example implementations.

## Edge Case Handling

This version includes improved validation and edge case handling across all data inputs.
See sample_data/realistic_data.csv for example datasets.

