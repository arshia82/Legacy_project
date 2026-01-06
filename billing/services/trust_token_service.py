# FILE: myfita/apps/backend/billing/services/trust_token_service.py
# REPLACE ENTIRE FILE

from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from dataclasses import dataclass
from typing import Optional
import uuid

from billing.models import TrustToken, AuditLog


@dataclass
class TokenValidationResult:
    """Result of token validation"""
    valid: bool
    reason: str = ""
    token: Optional[TrustToken] = None


@dataclass
class TokenUseResult:
    """Result of token use attempt"""
    success: bool
    reason: str = ""
    token: Optional[TrustToken] = None


class TrustTokenService:
    """Service for managing trust tokens with integrity verification"""

    @transaction.atomic
    def create_token(
        self,
        *,
        coach_id: uuid.UUID,
        athlete_id: uuid.UUID,
        program_id: uuid.UUID,
        gross_amount: int,
        commission_amount: int,
        net_amount: int,
        commission_rate,
        idempotency_key: str,
        created_by_ip: str = None,
        expires_in_minutes: int = 10,
    ) -> TrustToken:
        """
        Create a new trust token with idempotency support
        
        Args:
            coach_id: UUID of the coach
            athlete_id: UUID of the athlete
            program_id: UUID of the program
            gross_amount: Total amount in Toman
            commission_amount: Platform commission
            net_amount: Coach payout amount
            commission_rate: Commission rate as Decimal
            idempotency_key: Unique key for idempotent creation
            created_by_ip: IP address of creator
            expires_in_minutes: Token expiry time (default 10 minutes)
            
        Returns:
            TrustToken: Created or existing token
        """
        
        # Check for existing token with same idempotency key
        existing = TrustToken.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)

        token = TrustToken.objects.create(
            coach_id=coach_id,
            athlete_id=athlete_id,
            program_id=program_id,
            gross_amount=gross_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            commission_rate=commission_rate,
            idempotency_key=idempotency_key,
            created_by_ip=created_by_ip,
            expires_at=expires_at,
            status=TrustToken.Status.ACTIVE,
        )

        # Audit log
        AuditLog.objects.create(
            action=AuditLog.Action.TOKEN_CREATED,
            actor_type="system",
            actor_id=str(athlete_id),
            result="success",
            gross_amount=gross_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            request_summary={
                "coach_id": str(coach_id),
                "athlete_id": str(athlete_id),
                "program_id": str(program_id),
            },
        )

        return token

    def validate_token(self, token, coach_id: uuid.UUID = None) -> TokenValidationResult:
        """
        Validate a token for use
        
        Args:
            token: TrustToken object or UUID
            coach_id: Optional coach UUID for ownership verification
            
        Returns:
            TokenValidationResult with validation status
        """
        
        # Handle token_id passed instead of token object
        if isinstance(token, (str, uuid.UUID)):
            try:
                token = TrustToken.objects.get(id=token)
            except TrustToken.DoesNotExist:
                return TokenValidationResult(valid=False, reason="Token not found")

        # Check status
        if token.status != TrustToken.Status.ACTIVE:
            return TokenValidationResult(valid=False, reason=f"Token status is {token.status}")

        # Check expiry
        if token.expires_at <= timezone.now():
            return TokenValidationResult(valid=False, reason="Token expired")

        # Check integrity hash
        if not token.verify_integrity():
            AuditLog.objects.create(
                action=AuditLog.Action.TOKEN_TAMPERED,
                actor_type="system",
                result="failure",
                error_message="Integrity hash mismatch",
                request_summary={"token_id": str(token.id)},
            )
            return TokenValidationResult(valid=False, reason="Token integrity check failed")

        # Check coach match if provided
        if coach_id and token.coach_id != coach_id:
            return TokenValidationResult(valid=False, reason="Coach mismatch")

        return TokenValidationResult(valid=True, token=token)

    @transaction.atomic
    def use_token(self, token_id, coach_id: uuid.UUID = None, used_by_ip: str = None) -> TokenUseResult:
        """
        Mark a token as used (single-use enforcement with row-level locking)
        
        Args:
            token_id: Token UUID or TrustToken object
            coach_id: Optional coach UUID for verification
            used_by_ip: IP address of the user
            
        Returns:
            TokenUseResult with success status
        """
        
        # Handle token object passed instead of ID
        if isinstance(token_id, TrustToken):
            token_id = token_id.id

        try:
            # Lock the row for update to prevent race conditions
            token = TrustToken.objects.select_for_update().get(id=token_id)
        except TrustToken.DoesNotExist:
            return TokenUseResult(success=False, reason="Token not found")

        # Validate before use
        validation = self.validate_token(token, coach_id)
        if not validation.valid:
            return TokenUseResult(success=False, reason=validation.reason)

        # Mark as used
        token.mark_used(ip=used_by_ip)

        # Audit log
        AuditLog.objects.create(
            action=AuditLog.Action.TOKEN_USED,
            actor_type="coach",
            actor_id=str(coach_id) if coach_id else None,
            result="success",
            request_summary={
                "token_id": str(token.id),
                "used_by_ip": used_by_ip,
            },
        )

        return TokenUseResult(success=True, token=token)

    def get_token_preview(self, token_id: uuid.UUID) -> Optional[TrustToken]:
        """
        Get token for preview without validation (used internally)
        
        Args:
            token_id: Token UUID
            
        Returns:
            TrustToken or None
        """
        try:
            return TrustToken.objects.get(id=token_id)
        except TrustToken.DoesNotExist:
            return None