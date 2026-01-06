# FILE: myfita/apps/backend/programs/services/purchase_service.py

"""
PURCHASE SERVICE

Handles the complete purchase flow:
1. Create purchase record
2. Generate trust token (commission enforcement)
3. Process payment
4. Deliver program (PDF)

BP: "Transaction commission: platform take on program sales average 12%"
"""

import uuid
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from programs.models import Program, Purchase
from billing.models import TrustToken, CommissionConfig, AuditLog
from billing.services.commission_service import CommissionService


@dataclass
class PurchaseResult:
    """Result of purchase creation"""
    success: bool
    purchase: Optional[Purchase] = None
    trust_token: Optional[TrustToken] = None
    error_message: Optional[str] = None


class PurchaseService:
    """
    Service for managing program purchases.
    
    Integrates with:
    - CommissionService for fee calculation
    - TrustToken for payment security
    - PDFDeliveryService for content delivery
    """

    def __init__(self):
        self.commission_service = CommissionService()

    @transaction.atomic
    def create_purchase(
        self,
        athlete_id: uuid.UUID,
        program_id: uuid.UUID,
        client_ip: str = None
    ) -> PurchaseResult:
        """
        Create a new purchase with trust token.
        
        Args:
            athlete_id: UUID of the purchasing athlete
            program_id: UUID of the program to purchase
            client_ip: Client IP for audit
            
        Returns:
            PurchaseResult with purchase and trust token
        """
        
        # Get program
        try:
            program = Program.objects.select_related('coach').get(
                id=program_id,
                status=Program.Status.PUBLISHED
            )
        except Program.DoesNotExist:
            return PurchaseResult(
                success=False,
                error_message="Program not found or not available"
            )
        
        # Check for existing active purchase
        existing = Purchase.objects.filter(
            athlete_id=athlete_id,
            program=program,
            status__in=[Purchase.Status.PENDING, Purchase.Status.PAID, Purchase.Status.DELIVERED]
        ).first()
        
        if existing:
            if existing.status == Purchase.Status.PENDING:
                # Return existing pending purchase
                return PurchaseResult(
                    success=True,
                    purchase=existing,
                    trust_token=existing.trust_token
                )
            else:
                return PurchaseResult(
                    success=False,
                    error_message="You have already purchased this program"
                )
        
        # Calculate commission
        try:
            breakdown = self.commission_service.calculate(program.price_toman)
        except ValueError as e:
            return PurchaseResult(
                success=False,
                error_message=str(e)
            )
        
        # Generate idempotency key
        idempotency_key = f"purchase_{athlete_id}_{program_id}_{timezone.now().timestamp()}"
        
        # Create trust token
        trust_token = TrustToken.objects.create(
            program_id=program_id,
            coach_id=program.coach_id,
            athlete_id=athlete_id,
            gross_amount=breakdown.gross_amount,
            commission_amount=breakdown.commission_amount,
            net_amount=breakdown.net_amount,
            commission_rate=breakdown.rate,
            idempotency_key=idempotency_key,
            expires_at=timezone.now() + timedelta(hours=24),
            created_by_ip=client_ip,
        )
        
        # Create purchase
        purchase = Purchase.objects.create(
            athlete_id=athlete_id,
            program=program,
            trust_token=trust_token,
            price_paid_toman=breakdown.gross_amount,
            commission_amount=breakdown.commission_amount,
            net_amount=breakdown.net_amount,
            commission_rate=breakdown.rate,
            status=Purchase.Status.PENDING,
        )
        
        # Log purchase creation
        AuditLog.objects.create(
            action=AuditLog.Action.TOKEN_CREATED,
            actor_type='athlete',
            actor_id=str(athlete_id),
            target_id=purchase.id,
            result='success',
            gross_amount=breakdown.gross_amount,
            commission_amount=breakdown.commission_amount,
            net_amount=breakdown.net_amount,
            request_summary={
                'action': 'purchase_created',
                'program_id': str(program_id),
                'purchase_id': str(purchase.id),
            }
        )
        
        return PurchaseResult(
            success=True,
            purchase=purchase,
            trust_token=trust_token
        )

    @transaction.atomic
    def confirm_payment(
        self,
        purchase_id: uuid.UUID,
        payment_reference: str = None
    ) -> PurchaseResult:
        """
        Confirm payment for a purchase.
        
        Called after PSP confirms payment.
        """
        
        try:
            purchase = Purchase.objects.select_for_update().get(
                id=purchase_id,
                status=Purchase.Status.PENDING
            )
        except Purchase.DoesNotExist:
            return PurchaseResult(
                success=False,
                error_message="Purchase not found or already processed"
            )
        
        # Update purchase status
        purchase.status = Purchase.Status.PAID
        purchase.paid_at = timezone.now()
        purchase.save(update_fields=['status', 'paid_at'])
        
        # Mark trust token as used
        if purchase.trust_token:
            purchase.trust_token.mark_used()
        
        # Increment program purchase count
        program = purchase.program
        program.total_purchases += 1
        program.save(update_fields=['total_purchases'])
        
        # Log payment confirmation
        AuditLog.objects.create(
            action=AuditLog.Action.PAYOUT_COMPLETED,
            actor_type='system',
            target_id=purchase.id,
            result='success',
            gross_amount=purchase.price_paid_toman,
            commission_amount=purchase.commission_amount,
            net_amount=purchase.net_amount,
            request_summary={
                'action': 'payment_confirmed',
                'purchase_id': str(purchase.id),
                'payment_reference': payment_reference,
            }
        )
        
        return PurchaseResult(
            success=True,
            purchase=purchase
        )

    def get_athlete_purchases(self, athlete_id: uuid.UUID) -> list:
        """Get all purchases for an athlete"""
        return list(
            Purchase.objects.filter(
                athlete_id=athlete_id
            ).select_related(
                'program', 'program__coach'
            ).order_by('-created_at')
        )

    def get_coach_sales(self, coach_id: uuid.UUID) -> list:
        """Get all sales for a coach"""
        return list(
            Purchase.objects.filter(
                program__coach_id=coach_id,
                status__in=[Purchase.Status.PAID, Purchase.Status.DELIVERED]
            ).select_related(
                'program', 'athlete'
            ).order_by('-created_at')
        )