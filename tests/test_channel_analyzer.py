"""Tests for channel performance analyzer."""
import pytest
from channel_performance_analyzer import ChannelPerformanceAnalyzer


class TestChannelPerformanceAnalyzer:
    """Test channel performance analysis."""
    
    def test_initialization(self):
        """Test valid initialization."""
        analyzer = ChannelPerformanceAnalyzer("Hospital Channel", sales=100000, units_sold=5000)
        assert analyzer.channel_name == "Hospital Channel"
    
    def test_avg_price_calculation(self):
        """Test average price per unit."""
        analyzer = ChannelPerformanceAnalyzer("Retail", sales=50000, units_sold=1000)
        avg_price = analyzer.calculate_avg_price_per_unit()
        assert avg_price == pytest.approx(50.0, 0.1)
    
    def test_market_share(self):
        """Test market share calculation."""
        analyzer = ChannelPerformanceAnalyzer("Online", sales=100000, units_sold=2000)
        share = analyzer.calculate_market_contribution(total_market_sales=500000)
        assert share == pytest.approx(20.0, 0.1)
    
    def test_analysis_output(self):
        """Test analysis output."""
        analyzer = ChannelPerformanceAnalyzer("Clinic", sales=75000, units_sold=3000)
        result = analyzer.analyze(total_market_sales=300000)
        assert "channel" in result
        assert "market_share_percent" in result
        assert result["market_share_percent"] == pytest.approx(25.0, 0.1)
