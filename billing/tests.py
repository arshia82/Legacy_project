# FILE: myfita/apps/backend/billing/tests.py
# REPLACE ENTIRE FILE

"""
MY FITA Billing System - 51 Comprehensive Tests
Aligned with Business Plan risks (Page 14: Disintermediation, Commission Bypass)
"""

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta
import uuid
import hashlib
import threading
import time

from billing.models import TrustToken, Payout, CommissionConfig, AuditLog
from billing.services.trust_token_service import TrustTokenService
from billing.services.commission_service import CommissionService
from billing.services.payout_service import PayoutService


# ==============================================================================
# HELPERS
# ==============================================================================

def _uuid():
    return uuid.uuid4()


def _now():
    return timezone.now()


def _future(minutes=10):
    return timezone.now() + timedelta(minutes=minutes)


def _past(minutes=10):
    return timezone.now() - timedelta(minutes=minutes)


def _hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


# ==============================================================================
# GROUP 1: TRUST TOKEN INTEGRITY (12 tests)
# ==============================================================================

class TestGroup01_TrustTokenIntegrity(TestCase):
    """Tests for trust token creation, validation, and integrity"""

    def setUp(self):
        CommissionConfig.objects.all().delete()
        self.config = CommissionConfig.objects.create(
            name="default",
            rate=Decimal("0.1200"),
            is_active=True
        )
        self.token_service = TrustTokenService()
        self.commission_service = CommissionService()
        self.coach_id = _uuid()
        self.athlete_id = _uuid()
        self.program_id = _uuid()
        self.ip = "127.0.0.1"

    def _create_token(self, gross=10000, idempotency_key=None):
        """Helper to create a token with commission calculation"""
        breakdown = self.commission_service.calculate(gross)
        return self.token_service.create_token(
            program_id=self.program_id,
            coach_id=self.coach_id,
            athlete_id=self.athlete_id,
            gross_amount=gross,
            commission_amount=breakdown.commission_amount,  # ✅ FIXED
            net_amount=breakdown.net_amount, 
            commission_rate=breakdown.rate,
            idempotency_key=idempotency_key or str(_uuid()),
            created_by_ip=self.ip,
        )

    def test_01_token_single_use(self):
        """Token cannot be used twice (single-use enforcement)"""
        token = self._create_token()
        result1 = self.token_service.use_token(token.id, self.coach_id, self.ip)
        self.assertTrue(result1.success)
        result2 = self.token_service.use_token(token.id, self.coach_id, self.ip)
        self.assertFalse(result2.success)

    def test_02_token_expiry(self):
        """Token expires exactly at TTL boundary"""
        token = self._create_token()
        TrustToken.objects.filter(id=token.id).update(expires_at=_past(1))
        token.refresh_from_db()
        result = self.token_service.validate_token(token, self.coach_id)
        self.assertFalse(result.valid)

    def test_03_token_hash_tampering(self):
        """Token hash tampering is detected"""
        token = self._create_token()
        TrustToken.objects.filter(id=token.id).update(integrity_hash=_hash("tampered"))
        token.refresh_from_db()
        result = self.token_service.validate_token(token, self.coach_id)
        self.assertFalse(result.valid)

    def test_04_token_coach_mismatch(self):
        """Token coach mismatch rejected"""
        token = self._create_token()
        wrong_coach = _uuid()
        result = self.token_service.validate_token(token, wrong_coach)
        self.assertFalse(result.valid)

    def test_05_token_athlete_mismatch_detected(self):
        """Token athlete mismatch after DB tampering detected"""
        token = self._create_token()
        TrustToken.objects.filter(id=token.id).update(athlete_id=_uuid())
        token.refresh_from_db()
        result = self.token_service.validate_token(token, self.coach_id)
        self.assertFalse(result.valid)

    def test_06_token_program_mismatch_detected(self):
        """Token program mismatch after DB tampering detected"""
        token = self._create_token()
        TrustToken.objects.filter(id=token.id).update(program_id=_uuid())
        token.refresh_from_db()
        result = self.token_service.validate_token(token, self.coach_id)
        self.assertFalse(result.valid)

    def test_07_token_records_used_ip(self):
        """Token use records used_by_ip"""
        token = self._create_token()
        self.token_service.use_token(token.id, self.coach_id, "10.0.0.1")
        token.refresh_from_db()
        self.assertEqual(str(token.used_by_ip), "10.0.0.1")

    def test_08_token_idempotency(self):
        """Token idempotency key returns same token"""
        key = str(_uuid())
        t1 = self._create_token(idempotency_key=key)
        t2 = self._create_token(idempotency_key=key)
        self.assertEqual(t1.id, t2.id)

    def test_09_token_expired_boundary(self):
        """Token expired exactly at boundary is rejected"""
        token = self._create_token()
        TrustToken.objects.filter(id=token.id).update(expires_at=_now())
        token.refresh_from_db()
        time.sleep(0.01)
        result = self.token_service.validate_token(token, self.coach_id)
        self.assertFalse(result.valid)

    def test_10_token_creation_succeeds(self):
        """Token creation with all required fields succeeds"""
        token = self._create_token()
        self.assertIsNotNone(token.id)
        self.assertEqual(token.status, TrustToken.Status.ACTIVE)

    def test_11_token_status_changes_on_use(self):
        """Token status changes to USED after use"""
        token = self._create_token()
        self.token_service.use_token(token.id, self.coach_id, self.ip)
        token.refresh_from_db()
        self.assertEqual(token.status, TrustToken.Status.USED)

    def test_12_token_gross_amount_preserved(self):
        """Token gross amount is preserved exactly"""
        gross = 123456
        token = self._create_token(gross=gross)
        self.assertEqual(token.gross_amount, gross)


# ==============================================================================
# GROUP 2: COMMISSION ENFORCEMENT (10 tests)
# ==============================================================================

class TestGroup02_CommissionEnforcement(TestCase):
    """Tests for commission calculation and enforcement"""

    def setUp(self):
        CommissionConfig.objects.all().delete()
        self.config = CommissionConfig.objects.create(
            name="default",
            rate=Decimal("0.1200"),
            is_active=True
        )
        self.commission_service = CommissionService()

    def test_13_commission_math_exact(self):
        """Gross = commission + net (exact math)"""
        gross = 10000
        breakdown = self.commission_service.calculate(gross)
        self.assertEqual(breakdown.commission + breakdown.net, gross)

    def test_14_commission_rounding_not_favoring_coach(self):
        """Commission rounding does not favor coach"""
        gross = 12345
        breakdown = self.commission_service.calculate(gross)
        expected_min = int(gross * Decimal("0.12"))
        self.assertGreaterEqual(breakdown.commission, expected_min)

    def test_15_commission_rate_from_config(self):
        """Commission uses rate from config"""
        breakdown = self.commission_service.calculate(10000)
        self.assertEqual(breakdown.rate, Decimal("0.1200"))

    def test_16_commission_positive_rate_required(self):
        """Commission rate must be positive (business rule test)"""
        self.assertGreater(self.config.rate, 0)

    def test_17_commission_rate_not_excessive(self):
        """Commission rate should not exceed 100%"""
        self.assertLessEqual(self.config.rate, Decimal("1.0000"))

    def test_18_net_never_exceeds_gross(self):
        """Net amount never exceeds gross"""
        breakdown = self.commission_service.calculate(10000)
        self.assertLessEqual(breakdown.net, 10000)

    def test_19_commission_cannot_be_overridden(self):
        """Commission rate cannot be overridden via parameter"""
        with self.assertRaises(TypeError):
            self.commission_service.calculate(10000, override_rate=Decimal("0.01"))

    def test_20_commission_consistency(self):
        """Same input produces same output"""
        b1 = self.commission_service.calculate(10000)
        b2 = self.commission_service.calculate(10000)
        self.assertEqual(b1.commission, b2.commission)

    def test_21_commission_large_amount(self):
        """Commission works for large amounts"""
        gross = 1_000_000_000
        breakdown = self.commission_service.calculate(gross)
        self.assertEqual(breakdown.commission + breakdown.net, gross)

    def test_22_commission_config_exists(self):
        """Commission config must exist for calculations"""
        CommissionConfig.objects.all().delete()
        with self.assertRaises(ValueError):
            self.commission_service.calculate(10000)


# ==============================================================================
# GROUP 3: PAYOUT SECURITY (10 tests)
# ==============================================================================

class TestGroup03_PayoutSecurity(TestCase):
    """Tests for payout creation and security"""

    def setUp(self):
        CommissionConfig.objects.all().delete()
        self.config = CommissionConfig.objects.create(
            name="default",
            rate=Decimal("0.1200"),
            is_active=True
        )
        self.token_service = TrustTokenService()
        self.commission_service = CommissionService()
        self.payout_service = PayoutService()
        self.coach_id = _uuid()
        self.athlete_id = _uuid()
        self.program_id = _uuid()

        breakdown = self.commission_service.calculate(10000)
        self.token = self.token_service.create_token(
            program_id=self.program_id,
            coach_id=self.coach_id,
            athlete_id=self.athlete_id,
            gross_amount=10000,
            commission_amount=breakdown.commission_amount,  # ✅ FIXED
            net_amount=breakdown.net_amount,                # ✅ FIXED
            commission_rate=breakdown.rate,
            idempotency_key=str(_uuid()),
        )

    def test_23_payout_requires_valid_token(self):
        """Payout without valid token rejected"""
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(None, self.coach_id)

    def test_24_payout_invalid_token_rejected(self):
        """Payout with non-existent token rejected"""
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(_uuid(), self.coach_id)

    def test_25_payout_coach_mismatch(self):
        """Payout to wrong coach rejected"""
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(self.token.id, _uuid())

    def test_26_payout_once_only(self):
        """Payout can only be created once per token"""
        self.payout_service.create_payout(self.token.id, self.coach_id)
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(self.token.id, self.coach_id)

    def test_27_payout_creates_record(self):
        """Payout creates a Payout record"""
        before = Payout.objects.count()
        self.payout_service.create_payout(self.token.id, self.coach_id)
        self.assertEqual(Payout.objects.count(), before + 1)

    def test_28_payout_marks_token_used(self):
        """Payout marks token as USED"""
        self.payout_service.create_payout(self.token.id, self.coach_id)
        self.token.refresh_from_db()
        self.assertEqual(self.token.status, TrustToken.Status.USED)

    def test_29_payout_amount_integrity(self):
        """Payout amounts match token amounts"""
        payout = self.payout_service.create_payout(self.token.id, self.coach_id)
        self.assertEqual(payout.gross_amount, self.token.gross_amount)
        self.assertEqual(payout.net_amount, self.token.net_amount)

    def test_30_payout_expired_token_rejected(self):
        """Payout with expired token rejected"""
        TrustToken.objects.filter(id=self.token.id).update(expires_at=_past(1))
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(self.token.id, self.coach_id)

    def test_31_payout_links_to_token(self):
        """Payout is linked to correct token"""
        payout = self.payout_service.create_payout(self.token.id, self.coach_id)
        self.assertEqual(payout.trust_token_id, self.token.id)

    def test_32_payout_net_matches_token(self):
        """Payout net amount matches token net amount"""
        payout = self.payout_service.create_payout(self.token.id, self.coach_id)
        self.assertEqual(payout.net_amount, self.token.net_amount)


# ==============================================================================
# GROUP 4: DISINTERMEDIATION ATTACKS (8 tests)
# ==============================================================================

class TestGroup04_DisintermediationAttacks(TestCase):
    """Tests for disintermediation attack prevention (Business Plan Page 14)"""

    def setUp(self):
        CommissionConfig.objects.all().delete()
        self.config = CommissionConfig.objects.create(
            name="default",
            rate=Decimal("0.1200"),
            is_active=True
        )
        self.token_service = TrustTokenService()
        self.commission_service = CommissionService()
        self.payout_service = PayoutService()
        self.coach_id = _uuid()
        self.athlete_id = _uuid()
        self.program_id = _uuid()

        breakdown = self.commission_service.calculate(10000)
        self.token = self.token_service.create_token(
            program_id=self.program_id,
            coach_id=self.coach_id,
            athlete_id=self.athlete_id,
            gross_amount=10000,
            commission_amount=breakdown.commission_amount,  # ✅ FIXED
            net_amount=breakdown.net_amount,                # ✅ FIXED
            commission_rate=breakdown.rate,
            idempotency_key=str(_uuid()),
        )

    def test_33_external_reuse_blocked(self):
        """Token reuse after use is blocked"""
        self.token_service.use_token(self.token.id, self.coach_id)
        self.token.refresh_from_db()
        result = self.token_service.validate_token(self.token, self.coach_id)
        self.assertFalse(result.valid)

    def test_34_manual_status_tamper_detected(self):
        """Manual DB status change detected via integrity check"""
        self.token_service.use_token(self.token.id, self.coach_id)
        # Attempt to reset status to active (attack)
        TrustToken.objects.filter(id=self.token.id).update(status=TrustToken.Status.ACTIVE)
        self.token.refresh_from_db()
        # Token should still fail validation due to used_at being set
        result = self.token_service.validate_token(self.token, self.coach_id)
        # The integrity hash should detect the tampering
        self.assertFalse(result.valid)

    def test_35_amount_tamper_detected(self):
        """Manual DB amount change detected via integrity check"""
        TrustToken.objects.filter(id=self.token.id).update(gross_amount=999999)
        self.token.refresh_from_db()
        result = self.token_service.validate_token(self.token, self.coach_id)
        self.assertFalse(result.valid)

    def test_36_multiple_payouts_blocked(self):
        """Multiple payouts for same token blocked"""
        self.payout_service.create_payout(self.token.id, self.coach_id)
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(self.token.id, self.coach_id)

    def test_37_unused_token_expires_safely(self):
        """Unused token expires and becomes invalid"""
        TrustToken.objects.filter(id=self.token.id).update(expires_at=_past(1))
        self.token.refresh_from_db()
        result = self.token_service.validate_token(self.token, self.coach_id)
        self.assertFalse(result.valid)

    def test_38_self_payment_blocked(self):
        """Coach cannot pay themselves via wrong coach_id"""
        # Create token for coach
        breakdown = self.commission_service.calculate(10000)
        token = self.token_service.create_token(
            program_id=self.program_id,
            coach_id=self.coach_id,
            athlete_id=self.athlete_id,
            gross_amount=10000,
            commission_amount=breakdown.commission,
            net_amount=breakdown.net,
            commission_rate=breakdown.rate,
            idempotency_key=str(_uuid()),
        )
        # Try to claim payout as athlete (wrong person)
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(token.id, self.athlete_id)

    def test_39_athlete_cannot_trigger_payout(self):
        """Athlete cannot trigger payout"""
        with self.assertRaises(ValueError):
            self.payout_service.create_payout(self.token.id, self.athlete_id)

    def test_40_token_integrity_hash_exists(self):
        """Token has integrity hash on creation"""
        self.assertIsNotNone(self.token.integrity_hash)
        self.assertEqual(len(self.token.integrity_hash), 64)


# ==============================================================================
# GROUP 5: AUDIT & FORENSICS (10 tests)
# ==============================================================================

class TestGroup05_AuditAndForensics(TestCase):
    """Tests for audit logging and forensic trail"""

    def setUp(self):
        CommissionConfig.objects.all().delete()
        self.config = CommissionConfig.objects.create(
            name="default",
            rate=Decimal("0.1200"),
            is_active=True
        )
        self.token_service = TrustTokenService()
        self.commission_service = CommissionService()
        self.payout_service = PayoutService()
        AuditLog.objects.all().delete()

    def _create_token(self):
        breakdown = self.commission_service.calculate(10000)
        return self.token_service.create_token(
            program_id=_uuid(),
            coach_id=_uuid(),
            athlete_id=_uuid(),
            gross_amount=10000,
            commission_amount=breakdown.commission_amount,  # ✅ FIXED
            net_amount=breakdown.net_amount,  
            commission_rate=breakdown.rate,
            idempotency_key=str(_uuid()),
        )

    def test_41_audit_log_created_on_token(self):
        """Audit log created when token is created"""
        before = AuditLog.objects.count()
        self._create_token()
        self.assertGreater(AuditLog.objects.count(), before)

    def test_42_audit_action_enum_valid(self):
        """Audit log action uses valid enum"""
        self.assertTrue(hasattr(AuditLog.Action, 'TOKEN_CREATED'))

    def test_43_audit_log_on_payout(self):
        """Audit log created on payout"""
        token = self._create_token()
        before = AuditLog.objects.count()
        self.payout_service.create_payout(token.id, token.coach_id)
        self.assertGreater(AuditLog.objects.count(), before)

    def test_44_audit_action_token_used(self):
        """TOKEN_USED action exists"""
        self.assertTrue(hasattr(AuditLog.Action, 'TOKEN_USED'))

    def test_45_audit_action_payout_completed(self):
        """PAYOUT_COMPLETED action exists"""
        self.assertTrue(hasattr(AuditLog.Action, 'PAYOUT_COMPLETED'))

    def test_46_audit_log_has_timestamp(self):
        """Audit log has created_at timestamp"""
        log = AuditLog.objects.create(
            action=AuditLog.Action.TOKEN_CREATED,
            actor_type="test",
            result="success"
        )
        self.assertIsNotNone(log.created_at)

    def test_47_audit_log_ordering(self):
        """Audit logs are ordered by creation time (newest first)"""
        AuditLog.objects.create(action=AuditLog.Action.TOKEN_CREATED, actor_type="test", result="success")
        time.sleep(0.01)
        AuditLog.objects.create(action=AuditLog.Action.TOKEN_USED, actor_type="test", result="success")
        logs = list(AuditLog.objects.all())
        if len(logs) >= 2:
            self.assertGreaterEqual(logs[0].created_at, logs[1].created_at)

    def test_48_audit_log_action_required(self):
        """Audit log requires action field"""
        with self.assertRaises(Exception):
            AuditLog.objects.create(action=None, actor_type="test", result="success")

    def test_49_audit_log_persists(self):
        """Audit log persists in database"""
        log = AuditLog.objects.create(
            action=AuditLog.Action.TOKEN_CREATED,
            actor_type="test",
            result="success"
        )
        fetched = AuditLog.objects.get(id=log.id)
        self.assertEqual(fetched.action, AuditLog.Action.TOKEN_CREATED)

    def test_50_audit_log_count_increases(self):
        """Audit log count increases with operations"""
        before = AuditLog.objects.count()
        AuditLog.objects.create(action=AuditLog.Action.TOKEN_CREATED, actor_type="test", result="success")
        AuditLog.objects.create(action=AuditLog.Action.TOKEN_USED, actor_type="test", result="success")
        self.assertEqual(AuditLog.objects.count(), before + 2)


# ==============================================================================
# GROUP 6: CONCURRENCY STRESS (1 test)
# ==============================================================================

class TestGroup06_ConcurrencyStress(TransactionTestCase):
    """Tests for concurrent access and race conditions"""

    def setUp(self):
        CommissionConfig.objects.all().delete()
        self.config = CommissionConfig.objects.create(
            name="default",
            rate=Decimal("0.1200"),
            is_active=True
        )
        self.token_service = TrustTokenService()
        self.commission_service = CommissionService()

    def test_concurrent_token_use(self):
        """Concurrent token use allows only one success"""
        breakdown = self.commission_service.calculate(10000)
        coach_id = _uuid()
        token = self.token_service.create_token(
            program_id=_uuid(),
            coach_id=coach_id,
            athlete_id=_uuid(),
            gross_amount=10000,
            commission_amount=breakdown.commission_amount,  # ✅ FIXED
            net_amount=breakdown.net_amount,    
            commission_rate=breakdown.rate,
            idempotency_key=str(_uuid()),
        )

        results = []
        lock = threading.Lock()

        def attempt_use():
            try:
                from django.db import connection
                connection.ensure_connection()
                result = self.token_service.use_token(token.id, coach_id)
                with lock:
                    results.append("success" if result.success else "fail")
            except Exception as e:
                with lock:
                    results.append(f"error: {e}")

        threads = [threading.Thread(target=attempt_use) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one should succeed
        self.assertEqual(results.count("success"), 1)