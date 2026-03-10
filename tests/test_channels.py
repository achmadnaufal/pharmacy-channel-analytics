"""Tests for pharmacy channel analytics."""
import pytest
from channel_analyzer import PharmacyChannelAnalyzer


class TestChannelAnalytics:
    """Test channel analytics methods."""
    
    def test_channel_metrics(self):
        """Test channel metric calculation."""
        result = PharmacyChannelAnalyzer.calculate_channel_metrics(
            "Online",
            sales=[10000, 12000, 11000],
            transactions=[500, 600, 550],
            units_sold=[1000, 1200, 1100]
        )
        
        assert result['channel'] == 'Online'
        assert result['total_sales'] == 33000
        assert result['units_sold'] == 3300
    
    def test_channel_growth(self):
        """Test growth calculation."""
        growth = PharmacyChannelAnalyzer.calculate_channel_growth(10000, 12000)
        assert growth == 20.0
    
    def test_channel_mix(self):
        """Test channel mix analysis."""
        channels = {
            'Online': 50000,
            'Retail': 30000,
            'Wholesale': 20000,
        }
        
        mix = PharmacyChannelAnalyzer.channel_mix_analysis(channels)
        
        assert mix['Online']['percentage'] == 50.0
        assert mix['Retail']['percentage'] == 30.0
    
    def test_top_products(self):
        """Test identifying top products."""
        products = {
            'Product A': {'Online': 5000, 'Retail': 3000},
            'Product B': {'Online': 8000, 'Retail': 2000},
            'Product C': {'Online': 3000, 'Retail': 4000},
        }
        
        top = PharmacyChannelAnalyzer.identify_top_products_by_channel(
            products, 'Online', top_n=2
        )
        
        assert top[0]['product'] == 'Product B'
        assert top[0]['sales'] == 8000
    
    def test_channel_efficiency(self):
        """Test efficiency calculation."""
        efficiency = PharmacyChannelAnalyzer.calculate_channel_efficiency(
            sales=50000,
            inventory_investment=10000,
            staff_cost=5000
        )
        
        assert efficiency == round(50000 / 15000, 2)
