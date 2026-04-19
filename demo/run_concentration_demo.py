"""Pharmacy Channel Concentration demo.

Loads ``demo/sample_data.csv`` and prints HHI concentration, Pareto
80-20 ranking, and retail-vs-hospital channel split.

Run: python3 demo/run_concentration_demo.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

# Make ``src`` importable when running the script directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.channel_concentration_analyzer import ChannelConcentrationAnalyzer

DATA = os.path.join(os.path.dirname(__file__), "sample_data.csv")


def main() -> None:
    """Render the concentration dashboard for ``demo/sample_data.csv``."""
    print("=" * 62)
    print("  Pharmacy Channel Concentration — Demo")
    print("=" * 62)

    df = pd.read_csv(DATA)
    analyzer = ChannelConcentrationAnalyzer()

    print(f"\nLoaded {len(df)} outlet-month rows from {os.path.basename(DATA)}")
    print(f"  Unique outlets : {df['outlet_id'].nunique()}")
    print(f"  Channels       : {sorted(df['channel_type'].dropna().unique())}")
    print(f"  Cities         : {sorted(df['city'].dropna().unique())}")

    concentration = analyzer.compute_hhi(df)
    print("\nOutlet Concentration (HHI):")
    print(f"  HHI              : {concentration.hhi:,.0f}  ({concentration.band})")
    print(f"  HHI* normalised  : {concentration.hhi_normalised:.3f}")
    print(f"  Effective outlets: {concentration.effective_outlets:.2f}")
    print(f"  Active outlets   : {concentration.outlet_count}")
    print(f"  Zero-sales       : {concentration.zero_sales_outlets}")
    print(f"  Top outlet share : {concentration.top_outlet_share * 100:.1f}%")

    pareto = analyzer.pareto_ranking(df, cutoff=0.80)
    print("\nPareto 80/20 Ranking:")
    print(
        f"  {pareto.outlets_to_cutoff} of "
        f"{len(pareto.ranking)} outlets "
        f"({pareto.share_of_outlets * 100:.0f}%) drive 80% of revenue."
    )
    print(f"  {'Rank':>4}  {'Outlet':<10}  {'Revenue':>14}  {'Share':>7}  {'Cum%':>7}")
    for _, row in pareto.ranking.head(5).iterrows():
        print(
            f"  {int(row['rank']):>4}  {row['outlet_id']:<10}  "
            f"{row['revenue']:>14,.0f}  {row['revenue_share'] * 100:>6.1f}%  "
            f"{row['cumulative_share'] * 100:>6.1f}%"
        )

    split = analyzer.channel_split(df)
    print("\nChannel Split:")
    print(f"  Dominant channel : {split.dominant_channel} ({split.dominant_share * 100:.1f}%)")
    print(
        f"  {'Channel':<15}  {'Revenue':>14}  {'Share':>7}  "
        f"{'Outlets':>8}  {'HHI':>7}"
    )
    for _, row in split.per_channel.iterrows():
        print(
            f"  {row['channel_type']:<15}  {row['revenue']:>14,.0f}  "
            f"{row['revenue_share'] * 100:>6.1f}%  {int(row['outlet_count']):>8}  "
            f"{row['hhi_within_channel']:>7,.0f}"
        )

    print("\n" + "=" * 62)
    print("  Demo complete")
    print("=" * 62)


if __name__ == "__main__":
    main()
