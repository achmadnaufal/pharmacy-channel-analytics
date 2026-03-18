"""Pharmacy channel performance analysis module."""
from typing import Dict, List
import pandas as pd


class ChannelPerformanceAnalyzer:
    """Analyze pharmacy channel sales and performance metrics."""
    
    def __init__(self, channel_name: str, sales: float, units_sold: int):
        if sales < 0 or units_sold < 0:
            raise ValueError("Invalid metrics")
        self.channel_name = channel_name
        self.sales = sales
        self.units_sold = units_sold
    
    def calculate_avg_price_per_unit(self) -> float:
        """Calculate average price per unit."""
        return self.sales / self.units_sold if self.units_sold > 0 else 0
    
    def calculate_market_contribution(self, total_market_sales: float) -> float:
        """Calculate channel's % of total market."""
        return (self.sales / total_market_sales * 100) if total_market_sales > 0 else 0
    
    def analyze(self, total_market_sales: float = 0) -> Dict:
        """Generate channel analysis."""
        return {
            "channel": self.channel_name,
            "sales": round(self.sales, 2),
            "units_sold": self.units_sold,
            "avg_price_per_unit": round(self.calculate_avg_price_per_unit(), 2),
            "market_share_percent": round(self.calculate_market_contribution(total_market_sales), 2),
        }
