"""Channel performance forecasting for pharma analytics."""

from typing import Dict, List, Optional, Tuple
import math


class ChannelForecaster:
    """
    Forecast pharmacy channel performance using trend analysis.
    
    Supports:
    - Growth trajectory projections
    - Seasonality adjustments
    - Market share predictions
    - Channel health scoring
    """
    
    def __init__(self):
        """Initialize channel forecaster."""
        pass
    
    def forecast_channel_growth(
        self,
        channel_name: str,
        historical_sales: List[float],
        time_periods: List[str],
        forecast_periods: int = 4,
        growth_method: str = "exponential"  # linear, exponential, polynomial
    ) -> Dict:
        """
        Forecast future channel sales using historical trends.
        
        Args:
            channel_name: Name of pharmacy channel
            historical_sales: Historical sales values
            time_periods: Period labels (quarters, months, etc.)
            forecast_periods: Number of periods to forecast
            growth_method: Trend extrapolation method
        
        Returns:
            Dictionary with forecast, confidence intervals, and growth rate
        
        Raises:
            ValueError: If insufficient historical data (<3 periods)
        """
        if len(historical_sales) < 3:
            raise ValueError("Need at least 3 historical data points")
        if forecast_periods <= 0:
            raise ValueError("forecast_periods must be positive")
        
        # Calculate trend
        if growth_method == "linear":
            forecast, rate = self._linear_trend(historical_sales, forecast_periods)
        elif growth_method == "exponential":
            forecast, rate = self._exponential_trend(historical_sales, forecast_periods)
        else:
            forecast, rate = self._exponential_trend(historical_sales, forecast_periods)
        
        # Calculate confidence intervals (simplified)
        std_dev = self._calculate_std_dev(historical_sales)
        confidence_intervals = [
            {
                "period": f"Period {i+1}",
                "forecast": round(f, 2),
                "lower_bound": round(max(0, f - 2*std_dev), 2),
                "upper_bound": round(f + 2*std_dev, 2),
            }
            for i, f in enumerate(forecast)
        ]
        
        return {
            "channel_name": channel_name,
            "historical_periods": len(historical_sales),
            "forecast_periods": forecast_periods,
            "growth_method": growth_method,
            "average_growth_rate_pct": round(rate * 100, 2),
            "forecast": confidence_intervals,
            "trend_strength": self._calculate_trend_strength(historical_sales),
        }
    
    def _linear_trend(self, values: List[float], periods: int) -> Tuple[List[float], float]:
        """Calculate linear trend forecast."""
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        forecast = [intercept + slope * (n + i) for i in range(periods)]
        return forecast, slope / y_mean if y_mean != 0 else 0
    
    def _exponential_trend(self, values: List[float], periods: int) -> Tuple[List[float], float]:
        """Calculate exponential trend forecast."""
        n = len(values)
        
        # Calculate growth rate
        growth_rate = 0
        for i in range(n - 1):
            if values[i] > 0:
                growth_rate += (values[i + 1] - values[i]) / values[i]
        growth_rate = growth_rate / (n - 1)
        
        # Forecast
        last_value = values[-1]
        forecast = [last_value * ((1 + growth_rate) ** (i + 1)) for i in range(periods)]
        
        return forecast, growth_rate
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
    
    def _calculate_trend_strength(self, values: List[float]) -> str:
        """Assess strength of trend (weak, moderate, strong)."""
        if len(values) < 2:
            return "insufficient_data"
        
        changes = [abs(values[i+1] - values[i]) / max(values[i], 1) for i in range(len(values)-1)]
        avg_change = sum(changes) / len(changes)
        
        if avg_change < 0.05:
            return "weak"
        elif avg_change < 0.15:
            return "moderate"
        else:
            return "strong"
    
    def forecast_market_share(
        self,
        channel_sales: Dict[str, float],
        growth_rates: Dict[str, float],
        forecast_periods: int = 4
    ) -> Dict[str, List[float]]:
        """
        Forecast market share distribution across channels.
        
        Args:
            channel_sales: Current sales by channel
            growth_rates: Expected growth rates by channel (0.1 = 10%)
            forecast_periods: Number of periods to forecast
        
        Returns:
            Dictionary with market share trajectory per channel
        """
        if not channel_sales or not growth_rates:
            raise ValueError("channel_sales and growth_rates required")
        
        forecast = {}
        for channel, sales in channel_sales.items():
            growth = growth_rates.get(channel, 0)
            channel_forecast = [
                sales * ((1 + growth) ** (i + 1))
                for i in range(forecast_periods)
            ]
            forecast[channel] = [round(x, 2) for x in channel_forecast]
        
        # Calculate market shares
        market_shares = {}
        for period in range(forecast_periods):
            total = sum(forecast[ch][period] for ch in forecast)
            for channel in forecast:
                share_pct = (forecast[channel][period] / total * 100) if total > 0 else 0
                if channel not in market_shares:
                    market_shares[channel] = []
                market_shares[channel].append(round(share_pct, 1))
        
        return market_shares
    
    def identify_channel_winners_losers(
        self,
        historical_performance: Dict[str, List[float]],
        threshold_growth_pct: float = 10.0
    ) -> Dict[str, List[str]]:
        """
        Identify winning and losing channels based on growth trends.
        
        Args:
            historical_performance: Sales history by channel
            threshold_growth_pct: Growth threshold to classify as winner/loser
        
        Returns:
            Dictionary with 'winners' and 'losers' channel lists
        """
        if threshold_growth_pct <= 0:
            raise ValueError("threshold_growth_pct must be positive")
        
        channel_growth = {}
        
        for channel, sales_history in historical_performance.items():
            if len(sales_history) < 2:
                continue
            
            # Calculate CAGR (Compound Annual Growth Rate)
            start_value = sales_history[0]
            end_value = sales_history[-1]
            periods = len(sales_history) - 1
            
            if start_value > 0:
                cagr = ((end_value / start_value) ** (1 / periods) - 1) * 100
            else:
                cagr = 0
            
            channel_growth[channel] = cagr
        
        threshold = threshold_growth_pct
        
        return {
            "winners": sorted(
                [ch for ch, growth in channel_growth.items() if growth >= threshold],
                key=lambda x: channel_growth[x],
                reverse=True
            ),
            "losers": sorted(
                [ch for ch, growth in channel_growth.items() if growth < -threshold],
                key=lambda x: channel_growth[x]
            ),
            "growth_rates": {k: round(v, 2) for k, v in channel_growth.items()},
        }
