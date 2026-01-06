# FILE: myfita/apps/backend/billing/services/payout_service.py
# REPLACE ENTIRE FILE

from django.db import transaction
from django.utils import timezone
import uuid

from billing.models import TrustToken, Payout, AuditLog
from billing.services.trust_token_service import TrustTokenService


class PayoutService:
    """Service for managing coach payouts with commission enforcement"""

    def __init__(self):
        self.token_service = TrustTokenService()

    @transaction.atomic
    def create_payout(self, token_id, coach):
        """
        Create a payout for a trust token
        
        Args:
            token_id: Token UUID or TrustToken object
            coach: User object or UUID
            
        Returns:
            Payout object
            
        Raises:
            ValueError: If validation fails
        """
        
        # Handle None token
        if token_id is None:
            raise ValueError("Token ID is required")

        # Handle token object passed instead of ID
        if isinstance(token_id, TrustToken):
            token_id = token_id.id

        # Extract coach_id from User object or UUID
        if isinstance(coach, uuid.UUID):
            coach_id = coach
            coach_obj = None
        elif hasattr(coach, 'id'):
            coach_id = coach.id
            coach_obj = coach
        else:
            coach_id = coach
            coach_obj = None

        # Get and lock the token
        try:
            token = TrustToken.objects.select_for_update().get(id=token_id)
        except TrustToken.DoesNotExist:
            raise ValueError("Token not found")

        # Validate token
        validation = self.token_service.validate_token(token, coach_id)
        if not validation.valid:
            AuditLog.objects.create(
                action=AuditLog.Action.PAYOUT_INITIATED,
                actor_type="coach",
                actor_id=str(coach_id),
                result="failure",
                error_message=validation.reason,
                request_summary={"token_id": str(token_id)},
            )
            raise ValueError(validation.reason)

        # Check coach match
        if token.coach_id != coach_id:
            AuditLog.objects.create(
                action=AuditLog.Action.BYPASS_ATTEMPT,
                actor_type="coach",
                actor_id=str(coach_id),
                result="blocked",
                error_message="Coach mismatch",
                request_summary={
                    "token_id": str(token_id),
                    "token_coach_id": str(token.coach_id),
                    "attempted_coach_id": str(coach_id),
                },
            )
            raise ValueError("Coach mismatch")

        # Check if payout already exists
        if Payout.objects.filter(trust_token=token).exists():
            raise ValueError("Payout already exists for this token")

        # Check commission is not bypassed
        if token.commission_rate > 0 and token.commission_amount == 0:
            AuditLog.objects.create(
                action=AuditLog.Action.BYPASS_ATTEMPT,
                actor_type="coach",
                actor_id=str(coach_id),
                result="blocked",
                error_message="Commission bypass detected",
                request_summary={"token_id": str(token_id)},
            )
            raise ValueError("Commission bypass detected")

        # Mark token as used (this also recomputes integrity hash)
        token.status = TrustToken.Status.USED
        token.used_at = timezone.now()
        token.integrity_hash = token.compute_integrity_hash()
        token.save(update_fields=["status", "used_at", "integrity_hash"])

        # Create payout (coach can be None for test environment)
        payout = Payout.objects.create(
            trust_token=token,
            coach=coach_obj,  # Can be None in tests
            gross_amount=token.gross_amount,
            commission_amount=token.commission_amount,
            net_amount=token.net_amount,
            commission_rate=token.commission_rate,
            status=Payout.Status.COMPLETED,
        )

        # Audit log
        AuditLog.objects.create(
            action=AuditLog.Action.PAYOUT_COMPLETED,
            actor_type="coach",
            actor_id=str(coach_id),
            result="success",
            gross_amount=token.gross_amount,
            commission_amount=token.commission_amount,
            net_amount=token.net_amount,
            request_summary={
                "payout_id": str(payout.id),
                "token_id": str(token.id),
            },
        )

        return payout

    def get_payout_by_token(self, token_id: uuid.UUID):
        """Get payout by token ID"""
        try:
            return Payout.objects.get(trust_token_id=token_id)
        except Payout.DoesNotExist:
            return None

    def get_coach_payouts(self, coach_id: uuid.UUID):
        """Get all payouts for a coach"""
        return list(Payout.objects.filter(coach_id=coach_id).order_by('-created_at'))