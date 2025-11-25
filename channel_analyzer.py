"""Pharmacy channel analytics and KPI tracking."""

from typing import Dict, List
import numpy as np


class PharmacyChannelAnalyzer:
    """Analyze pharmacy channel performance and sales metrics."""
    
    @staticmethod
    def calculate_channel_metrics(
        channel_name: str,
        sales: List[float],
        transactions: List[int],
        units_sold: List[int]
    ) -> Dict:
        """
        Calculate channel performance metrics.
        
        Args:
            channel_name: Name of pharmacy channel
            sales: Sales revenue per period
            transactions: Transaction count per period
            units_sold: Units sold per period
            
        Returns:
            Dictionary with channel KPIs
        """
        total_sales = sum(sales)
        total_transactions = sum(transactions)
        total_units = sum(units_sold)
        
        avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0
        avg_unit_price = total_sales / total_units if total_units > 0 else 0
        
        return {
            "channel": channel_name,
            "total_sales": round(total_sales, 2),
            "transaction_count": total_transactions,
            "units_sold": total_units,
            "avg_transaction_value": round(avg_transaction, 2),
            "avg_unit_price": round(avg_unit_price, 2),
            "periods": len(sales),
        }
    
    @staticmethod
    def calculate_channel_growth(
        previous_period_sales: float,
        current_period_sales: float
    ) -> float:
        """
        Calculate year-over-year or period-over-period growth.
        
        Args:
            previous_period_sales: Previous period total sales
            current_period_sales: Current period total sales
            
        Returns:
            Growth rate as percentage
        """
        if previous_period_sales == 0:
            return 0.0
        
        growth = (current_period_sales - previous_period_sales) / previous_period_sales * 100
        return round(growth, 2)
    
    @staticmethod
    def channel_mix_analysis(
        channels: Dict[str, float]
    ) -> Dict:
        """
        Analyze sales mix across channels.
        
        Args:
            channels: Dict of channel names and their sales
            
        Returns:
            Dictionary with mix percentages
        """
        total_sales = sum(channels.values())
        
        mix = {}
        for channel, sales in channels.items():
            percentage = (sales / total_sales * 100) if total_sales > 0 else 0
            mix[channel] = {
                "sales": round(sales, 2),
                "percentage": round(percentage, 2),
            }
        
        return mix
    
    @staticmethod
    def identify_top_products_by_channel(
        products: Dict[str, Dict[str, float]],
        channel: str,
        top_n: int = 10
    ) -> List[Dict]:
        """
        Identify top selling products in a channel.
        
        Args:
            products: Dict mapping product names to channel sales
            channel: Channel name to analyze
            top_n: Number of top products to return
            
        Returns:
            List of top products with sales data
        """
        channel_products = []
        
        for product_name, channels_data in products.items():
            if channel in channels_data:
                channel_products.append({
                    "product": product_name,
                    "sales": channels_data[channel],
                })
        
        # Sort by sales descending
        sorted_products = sorted(channel_products, key=lambda x: x['sales'], reverse=True)
        
        return sorted_products[:top_n]
    
    @staticmethod
    def calculate_channel_efficiency(
        sales: float,
        inventory_investment: float,
        staff_cost: float
    ) -> float:
        """
        Calculate channel operational efficiency ratio.
        
        Args:
            sales: Total sales revenue
            inventory_investment: Inventory investment amount
            staff_cost: Total staff costs
            
        Returns:
            Efficiency score (sales per unit cost)
        """
        total_cost = inventory_investment + staff_cost
        
        if total_cost == 0:
            return 0.0
        
        efficiency = sales / total_cost
        return round(efficiency, 2)
