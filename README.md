# Pharmacy Channel Analytics

![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Last Commit](https://img.shields.io/github/last-commit/achmadnaufal/pharmacy-channel-analytics)
![Tests](https://img.shields.io/badge/tests-132%20passing-brightgreen)
![Domain](https://img.shields.io/badge/domain-Pharma%20BI-9cf)

> Retail, hospital, and online pharmacy channel performance analytics — Channel Performance Index (CPI), period-over-period growth, channel mix optimisation, ROI benchmarking, outlet segmentation, and seasonal demand adjustment.

---

## ✨ Features

| Module | Description |
|---|---|
| **Channel Performance Index (CPI)** | Composite 0–100 score from sales share, target attainment, and ROI |
| **Growth Rates** | QoQ / MoM growth with trend labels (growing / stable / declining) |
| **Channel Mix Optimiser** | Resource allocation across hospital, retail, online |
| **Market Share Tracker** | Brand × channel share evolution |
| **Outlet Segmentation Engine** | Volume + brand-loyalty tiering for pharmacy outlets |
| **Seasonal Demand Adjuster** | Cycle-adjusted target setting |
| **Channel ROI Analyzer** | Promotional spend efficiency, NPV-style portfolio summary |
| **Channel Forecast** | Time-series projection per channel |

---

## 🚀 Quick Start

```bash
git clone https://github.com/achmadnaufal/pharmacy-channel-analytics.git
cd pharmacy-channel-analytics
pip install -r requirements.txt

# Run the CLI demo
python3 demo/run_demo.py
```

---

## 🧪 Usage

### Python API

```python
from src.main import PharmacyChannelAnalytics

analyzer = PharmacyChannelAnalytics()
df = analyzer.load_data("sample_data/channel_performance.csv")

cpi = analyzer.calculate_channel_performance_index(
    df,
    channel_col="channel",
    sales_col="sales_value",
    target_col="sales_target",
    cost_col="channel_cost",
)
growth = analyzer.get_channel_growth_rates(df)
```

Expected CSV columns:

```
channel, period, sales_value, sales_target, channel_cost, region
```

### Demo output

```text
$ python3 demo/run_demo.py
==============================================================
  Pharmacy Channel Analytics — Demo
==============================================================

✓ Loaded 12 channel records from channel_performance.csv
  Channels : ['Hospital', 'Online', 'Retail']
  Periods  : ['2025-Q1', '2025-Q2', '2025-Q3', '2025-Q4']
  Regions  : ['Java', 'National']

✓ Channel Performance Index (CPI):
  Channel           Total Sales   Target Att%     ROI %     CPI  Band
  ----------------------------------------------------------------------
  Hospital            2,135,000        103.6%    911.8%   100.0  Excellent
  Retail                800,000        108.1%    561.2%   100.0  Excellent
  Online                280,000        112.0%    566.7%    77.4  Excellent

✓ Period-over-Period Growth Rates:
  Channel         Period               Sales    Growth %  Trend
  ------------------------------------------------------------
  Hospital        2025-Q1            520,000        base  base_period
  Hospital        2025-Q2            540,000       +3.8%  stable
  Hospital        2025-Q3            510,000       -5.6%  declining
  Hospital        2025-Q4            565,000      +10.8%  growing
  Online          2025-Q1             45,000        base  base_period
  Online          2025-Q2             62,000      +37.8%  growing
  Online          2025-Q3             78,000      +25.8%  growing
  Online          2025-Q4             95,000      +21.8%  growing
  Retail          2025-Q1            180,000        base  base_period
  Retail          2025-Q2            195,000       +8.3%  growing
  Retail          2025-Q3            205,000       +5.1%  growing
  Retail          2025-Q4            220,000       +7.3%  growing

✓ Channel Ranking Summary:
  Top performer    : Hospital — CPI 100.0 (Excellent)
                     Sales $2,135,000 | Target attainment 103.6% | ROI 911.8%
  Needs attention  : Online — CPI 77.4 (Excellent)
                     Sales $280,000 | Target attainment 112.0% | ROI 566.7%

==============================================================
  ✅ Demo complete
==============================================================
```

---

## 🏗 Architecture

```mermaid
flowchart LR
    A[CSV / Excel<br/>Channel Sales Data] --> B[PharmacyChannelAnalytics<br/>load + validate]
    B --> C[Channel Performance Index<br/>sales share + target + ROI]
    B --> D[Growth Rate Tracking<br/>QoQ / MoM trends]
    B --> E[Channel Mix Optimiser<br/>resource allocation]
    B --> F[Market Share Tracker<br/>brand × channel]
    B --> G[Outlet Segmentation<br/>volume + loyalty tiers]
    B --> H[Channel ROI Analyzer<br/>portfolio summary]
    B --> I[Seasonal Demand Adjuster<br/>cycle correction]
    C & D & E & F & G & H & I --> J[DataFrame / CSV / Excel Export]
```

---

## 🛠 Tech Stack

- **Python 3.9+**
- **pandas / numpy** — analytics
- **pytest** — 132-test suite
- **openpyxl** — Excel I/O

---

## 📁 Project Structure

```
pharmacy-channel-analytics/
├── channel_analyzer.py             # Top-level analyzer entrypoint
├── channel_performance_analyzer.py
├── src/
│   ├── channel_roi_analyzer.py
│   ├── channel_mix_optimizer.py
│   ├── outlet_segmentation_engine.py
│   ├── market_share_tracker.py
│   ├── seasonal_demand_adjuster.py
│   ├── channel_forecast.py
│   └── ...
├── sample_data/                    # CSV samples for demo
├── demo/
│   └── run_demo.py                 # CLI demo
├── tests/                          # 132 unit tests
├── examples/basic_usage.py
├── requirements.txt
└── LICENSE
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

> Built by [Achmad Naufal](https://github.com/achmadnaufal) | Lead Data Analyst | Power BI · SQL · Python · GIS
