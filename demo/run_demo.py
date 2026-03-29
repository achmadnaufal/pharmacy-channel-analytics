"""
Pharmacy Channel Analytics — live demo
Run: python3 demo/run_demo.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from src.main import PharmacyChannelAnalytics

DATA = os.path.join(os.path.dirname(__file__), "../sample_data/channel_performance.csv")

print("=" * 62)
print("  Pharmacy Channel Analytics — Demo")
print("=" * 62)

analyzer = PharmacyChannelAnalytics()
df = analyzer.load_data(DATA)
print(f"\n✓ Loaded {len(df)} channel records from {os.path.basename(DATA)}")
print(f"  Channels : {sorted(df['channel'].unique())}")
print(f"  Periods  : {sorted(df['period'].unique())}")
print(f"  Regions  : {sorted(df['region'].unique())}")

# Channel Performance Index
cpi = analyzer.calculate_channel_performance_index(
    df,
    channel_col="channel",
    sales_col="sales_value",
    target_col="sales_target",
    cost_col="channel_cost",
)
print(f"\n✓ Channel Performance Index (CPI):")
print(f"  {'Channel':<14}  {'Total Sales':>13}  {'Target Att%':>12}  {'ROI %':>8}  {'CPI':>6}  {'Band':<15}")
print(f"  {'-'*70}")
for _, row in cpi.iterrows():
    print(f"  {row['channel']:<14}  {row['sales_value']:>13,.0f}  "
          f"{row['target_attainment_pct']:>11.1f}%  {row['roi_pct']:>7.1f}%  {row['cpi_score']:>6.1f}  {row['cpi_band']:<15}")

# Growth rates
growth = analyzer.get_channel_growth_rates(
    df,
    channel_col="channel",
    sales_col="sales_value",
    period_col="period",
)
print(f"\n✓ Period-over-Period Growth Rates:")
print(f"  {'Channel':<14}  {'Period':<12}  {'Sales':>12}  {'Growth %':>10}  {'Trend'}")
print(f"  {'-'*60}")
for _, row in growth.iterrows():
    growth_str = f"{row['growth_rate_pct']:+.1f}%" if pd.notna(row['growth_rate_pct']) else "base"
    print(f"  {row['channel']:<14}  {row['period']:<12}  {row['sales_value']:>12,.0f}  {growth_str:>10}  {row['growth_trend']}")

# Summary: best and worst channel
best = cpi.iloc[0]
worst = cpi.iloc[-1]
print(f"\n✓ Channel Ranking Summary:")
print(f"  Top performer    : {best['channel']} — CPI {best['cpi_score']:.1f} ({best['cpi_band']})")
print(f"                     Sales ${best['sales_value']:,.0f} | Target attainment {best['target_attainment_pct']:.1f}% | ROI {best['roi_pct']:.1f}%")
print(f"  Needs attention  : {worst['channel']} — CPI {worst['cpi_score']:.1f} ({worst['cpi_band']})")
print(f"                     Sales ${worst['sales_value']:,.0f} | Target attainment {worst['target_attainment_pct']:.1f}% | ROI {worst['roi_pct']:.1f}%")

print("\n" + "=" * 62)
print("  ✅ Demo complete")
print("=" * 62)
