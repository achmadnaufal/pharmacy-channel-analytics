"""Tests for channel forecasting."""

import pytest
from src.channel_forecast import ChannelForecaster


class TestChannelForecaster:
    """Test channel forecasting methods."""
    
    @pytest.fixture
    def forecaster(self):
        return ChannelForecaster()
    
    def test_forecast_growth(self, forecaster):
        """Test sales growth forecasting."""
        historical = [100, 120, 140, 160]
        
        result = forecaster.forecast_channel_growth(
            channel_name="Hospital",
            historical_sales=historical,
            time_periods=["Q1", "Q2", "Q3", "Q4"],
            forecast_periods=4,
            growth_method="linear"
        )
        
        assert result["channel_name"] == "Hospital"
        assert len(result["forecast"]) == 4
        assert result["average_growth_rate_pct"] > 0
    
    def test_market_share_forecast(self, forecaster):
        """Test market share prediction."""
        sales = {"Hospital": 1000, "Retail": 800, "Online": 200}
        growth = {"Hospital": 0.05, "Retail": 0.10, "Online": 0.20}
        
        result = forecaster.forecast_market_share(sales, growth, forecast_periods=4)
        
        assert "Hospital" in result
        assert "Retail" in result
        assert len(result["Hospital"]) == 4
    
    def test_winners_losers(self, forecaster):
        """Test identification of winning channels."""
        performance = {
            "Hospital": [1000, 1200, 1400, 1600],
            "Retail": [500, 480, 450, 400],
            "Online": [100, 100, 100, 100],
        }
        
        result = forecaster.identify_channel_winners_losers(
            performance,
            threshold_growth_pct=5.0
        )
        
        assert "Hospital" in result["winners"]
        assert "Retail" in result["losers"]
