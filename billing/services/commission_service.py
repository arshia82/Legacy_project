# FILE: myfita/apps/backend/billing/services/commission_service.py
# REPLACE ENTIRE FILE

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

from billing.models import CommissionConfig


@dataclass
class CommissionBreakdown:
    """Commission calculation result"""
    gross: int
    commission_amount: int  # ✅ Changed from 'commission'
    net_amount: int         # ✅ Changed from 'net'
    rate: Decimal
    
    # Backward compatibility aliases
    @property
    def commission(self):
        return self.commission_amount
    
    @property
    def net(self):
        return self.net_amount


class CommissionService:
    """Service for calculating platform commissions"""

    def calculate(self, gross_amount: int) -> CommissionBreakdown:
        """
        Calculate commission breakdown for a gross amount
        
        Args:
            gross_amount: Total amount in Toman
            
        Returns:
            CommissionBreakdown with calculated values
            
        Raises:
            ValueError: If gross amount is invalid
        """
        
        if gross_amount <= 0:
            raise ValueError("Gross amount must be positive")

        # Get active commission rate
        rate = CommissionConfig.get_active_rate()

        if rate <= 0:
            raise ValueError("Commission rate must be positive")

        if rate > Decimal("1.0000"):
            raise ValueError("Commission rate cannot exceed 100%")

        # Calculate commission (round up to not favor coach)
        commission = int(
            (Decimal(gross_amount) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        net = gross_amount - commission

        return CommissionBreakdown(
            gross=gross_amount,
            commission_amount=commission,
            net_amount=net,
            rate=rate,
        )