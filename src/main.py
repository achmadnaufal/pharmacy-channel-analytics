"""
Retail and hospital pharmacy channel performance analytics

Author: github.com/achmadnaufal
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any


class PharmacyChannelAnalytics:
    """Pharmacy channel performance analyzer"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load data from CSV or Excel file."""
        p = Path(filepath)
        if p.suffix in (".xlsx", ".xls"):
            return pd.read_excel(filepath)
        return pd.read_csv(filepath)

    def validate(self, df: pd.DataFrame) -> bool:
        """Basic validation of input data."""
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        return True

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess input data."""
        df = df.copy()
        # Drop fully empty rows
        df.dropna(how="all", inplace=True)
        # Standardize column names
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        return df

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run core analysis and return summary metrics."""
        df = self.preprocess(df)
        result = {
            "total_records": len(df),
            "columns": list(df.columns),
            "missing_pct": (df.isnull().sum() / len(df) * 100).round(1).to_dict(),
        }
        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            result["summary_stats"] = numeric_df.describe().round(3).to_dict()
            result["totals"] = numeric_df.sum().round(2).to_dict()
            result["means"] = numeric_df.mean().round(3).to_dict()
        return result

    def run(self, filepath: str) -> Dict[str, Any]:
        """Full pipeline: load → validate → analyze."""
        df = self.load_data(filepath)
        self.validate(df)
        return self.analyze(df)

    def to_dataframe(self, result: Dict) -> pd.DataFrame:
        """Convert analysis result to DataFrame for export."""
        rows = []
        for k, v in result.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    rows.append({"metric": f"{k}.{kk}", "value": vv})
            else:
                rows.append({"metric": k, "value": v})
        return pd.DataFrame(rows)

    def calculate_channel_performance_index(
        self,
        df: pd.DataFrame,
        channel_col: str = "channel",
        sales_col: str = "sales_value",
        target_col: Optional[str] = "sales_target",
        cost_col: Optional[str] = "channel_cost",
    ) -> pd.DataFrame:
        """
        Calculate a composite Channel Performance Index (CPI) for each channel.

        The CPI combines target attainment, growth, and cost efficiency into
        a single 0–100 score for channel comparison and resource allocation.

        Args:
            df: DataFrame with channel sales data (at least channel + sales columns)
            channel_col: Column name for channel type (e.g. "hospital", "retail")
            sales_col: Column name for sales value
            target_col: Optional column with sales target. If present, target
                        attainment is included in CPI score.
            cost_col: Optional column with channel cost. If present, ROI is
                      factored into CPI score.

        Returns:
            DataFrame with channel, total_sales, target_attainment_pct (if targets
            present), roi_pct (if costs present), cpi_score, and cpi_band

        Raises:
            ValueError: If required columns are missing or DataFrame is empty

        Example:
            >>> df = pd.DataFrame({
            ...     "channel": ["Hospital", "Retail", "Retail", "Hospital"],
            ...     "sales_value": [500000, 200000, 220000, 480000],
            ...     "sales_target": [450000, 180000, 200000, 500000],
            ...     "channel_cost": [50000, 30000, 30000, 50000],
            ... })
            >>> cpi = analyzer.calculate_channel_performance_index(df)
            >>> print(cpi[["channel", "cpi_score", "cpi_band"]])
        """
        if df.empty:
            raise ValueError("DataFrame cannot be empty")
        if channel_col not in df.columns:
            raise ValueError(f"Column '{channel_col}' not found in DataFrame")
        if sales_col not in df.columns:
            raise ValueError(f"Column '{sales_col}' not found in DataFrame")

        df = df.copy()
        df[sales_col] = pd.to_numeric(df[sales_col], errors="coerce").fillna(0)

        agg: dict = {sales_col: "sum"}

        if target_col and target_col in df.columns:
            df[target_col] = pd.to_numeric(df[target_col], errors="coerce").fillna(0)
            agg[target_col] = "sum"

        if cost_col and cost_col in df.columns:
            df[cost_col] = pd.to_numeric(df[cost_col], errors="coerce").fillna(0)
            agg[cost_col] = "sum"

        grouped = df.groupby(channel_col).agg(agg).reset_index()

        # Total sales share (0–40 pts)
        total_sales = grouped[sales_col].sum()
        grouped["sales_share_pct"] = (
            grouped[sales_col] / total_sales * 100 if total_sales > 0 else 0.0
        )
        grouped["sales_share_score"] = grouped["sales_share_pct"].apply(
            lambda x: min(40, x * 2)
        )

        # Target attainment (0–35 pts)
        if target_col and target_col in grouped.columns:
            grouped["target_attainment_pct"] = (
                grouped[sales_col] / grouped[target_col] * 100
            ).where(grouped[target_col] > 0, 0).round(1)
            grouped["target_score"] = grouped["target_attainment_pct"].apply(
                lambda x: min(35, x * 0.35)
            )
        else:
            grouped["target_attainment_pct"] = None
            grouped["target_score"] = 17.5  # Neutral when no target

        # ROI (0–25 pts)
        if cost_col and cost_col in grouped.columns:
            grouped["roi_pct"] = (
                (grouped[sales_col] - grouped[cost_col]) / grouped[cost_col] * 100
            ).where(grouped[cost_col] > 0, 0).round(1)
            grouped["roi_score"] = grouped["roi_pct"].apply(
                lambda x: min(25, max(0, x / 4 * 1))
            )
        else:
            grouped["roi_pct"] = None
            grouped["roi_score"] = 12.5  # Neutral when no cost data

        # Composite CPI
        grouped["cpi_score"] = (
            grouped["sales_share_score"] + grouped["target_score"] + grouped["roi_score"]
        ).round(1)

        # CPI band
        def band(score):
            if score >= 75:
                return "Excellent"
            elif score >= 55:
                return "Good"
            elif score >= 35:
                return "Fair"
            else:
                return "Underperforming"

        grouped["cpi_band"] = grouped["cpi_score"].apply(band)

        # Clean output
        output_cols = [channel_col, sales_col, "sales_share_pct"]
        if target_col and target_col in grouped.columns:
            output_cols += ["target_attainment_pct"]
        if cost_col and cost_col in grouped.columns:
            output_cols += ["roi_pct"]
        output_cols += ["cpi_score", "cpi_band"]

        return grouped[output_cols].sort_values("cpi_score", ascending=False).reset_index(drop=True)

    def get_channel_growth_rates(
        self,
        df: pd.DataFrame,
        channel_col: str = "channel",
        sales_col: str = "sales_value",
        period_col: str = "period",
    ) -> pd.DataFrame:
        """
        Calculate period-over-period growth rates per channel.

        Args:
            df: DataFrame with channel, period, and sales columns
            channel_col: Column for channel identifier
            sales_col: Column for sales value
            period_col: Column for time period (sortable — date, month, quarter)

        Returns:
            DataFrame with channel, period, sales, prior_period_sales,
            growth_rate_pct, and growth_trend

        Raises:
            ValueError: If required columns missing or DataFrame empty

        Example:
            >>> df = pd.DataFrame({
            ...     "channel": ["Retail","Retail","Hospital","Hospital"],
            ...     "period": ["2025-Q3","2025-Q4","2025-Q3","2025-Q4"],
            ...     "sales_value": [100000, 120000, 200000, 190000],
            ... })
            >>> growth = analyzer.get_channel_growth_rates(df)
        """
        if df.empty:
            raise ValueError("DataFrame cannot be empty")
        missing = [c for c in (channel_col, sales_col, period_col) if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df = df.copy()
        df[sales_col] = pd.to_numeric(df[sales_col], errors="coerce").fillna(0)

        agg = df.groupby([channel_col, period_col])[sales_col].sum().reset_index()
        agg = agg.sort_values([channel_col, period_col])

        agg["prior_period_sales"] = agg.groupby(channel_col)[sales_col].shift(1)
        agg["growth_rate_pct"] = (
            (agg[sales_col] - agg["prior_period_sales"]) / agg["prior_period_sales"] * 100
        ).round(1)

        def trend(rate):
            if pd.isna(rate):
                return "base_period"
            if rate > 5:
                return "growing"
            if rate < -5:
                return "declining"
            return "stable"

        agg["growth_trend"] = agg["growth_rate_pct"].apply(trend)

        return agg.reset_index(drop=True)
