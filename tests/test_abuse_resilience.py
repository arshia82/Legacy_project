# tests/test_abuse_resilience.py

from uuid import uuid4

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from users.services.verification_service import verification_service
from users.models import CoachVerificationRequest

User = get_user_model()


def unique_phone() -> str:
    """
    Generates a phone number that remains UNIQUE
    even after any normalization in UserManager.
    """
    return f"09{uuid4().int % 10**9:09d}"


class AbuseResilienceTests(TestCase):
    """
    High‑intensity abuse & security stress tests for MY‑FITA verification system.

    These tests defend against:
    - duplicate onboarding abuse
    - privilege escalation
    - admin queue poisoning
    - marketplace trust bypass
    - state machine corruption

    Fully aligned with MY‑FITA Business Plan:
    Trust-first, commission-based, verified-only supply.
    """

    def setUp(self):
        self.coach = User.objects.create_user(
            phone=unique_phone(),
            role="coach"
        )

        self.other_coach = User.objects.create_user(
            phone=unique_phone(),
            role="coach"
        )

        self.admin = User.objects.create_user(
            phone=unique_phone(),
            role="admin",
            is_staff=True
        )

    # --------------------------------------------------
    # DUPLICATE REQUEST ABUSE
    # --------------------------------------------------

    def test_cannot_create_multiple_active_requests(self):
        """
        A coach must not be able to spam verification requests.
        Prevents admin queue flooding.
        """
        verification_service.create_request(self.coach)

        with self.assertRaises(ValidationError):
            verification_service.create_request(self.coach)

    # --------------------------------------------------
    # PRIVILEGE ESCALATION
    # --------------------------------------------------

    def test_other_user_cannot_submit_request(self):
        """
        Another coach must never be able to submit
        someone else's verification request.
        """
        req = verification_service.create_request(self.coach)

        with self.assertRaises(ValidationError):
            verification_service.submit_request(req, self.other_coach)

    # --------------------------------------------------
    # STATE MACHINE ABUSE
    # --------------------------------------------------

    def test_double_submission_is_blocked(self):
        """
        Draft → Pending is a one‑way transition.
        Replay attacks must fail.
        """
        req = verification_service.create_request(self.coach)
        verification_service.submit_request(req, self.coach)

        with self.assertRaises(ValidationError):
            verification_service.submit_request(req, self.coach)

    # --------------------------------------------------
    # ADMIN PRIVILEGE ABUSE
    # --------------------------------------------------

    def test_non_admin_cannot_approve(self):
        """
        Coaches must never be able to self‑verify.
        """
        req = verification_service.create_request(self.coach)

        with self.assertRaises(ValidationError):
            verification_service.approve_request(req, self.coach)

    def test_double_approval_is_idempotent(self):
        """
        Repeated admin approval must not corrupt state.
        Defensive against retry storms & race conditions.
        """
        req = verification_service.create_request(self.coach)

        verification_service.approve_request(req, self.admin)
        verification_service.approve_request(req, self.admin)  # second call

        self.coach.refresh_from_db()
        self.assertTrue(self.coach.is_verified)

    # --------------------------------------------------
    # MARKETPLACE TRUST BYPASS
    # --------------------------------------------------

    def test_unverified_coach_not_visible(self):
        """
        Core business rule:
        Unverified supply MUST NOT enter marketplace.
        """
        self.assertFalse(
            verification_service.can_coach_be_visible(self.coach)
        )

    def test_verified_coach_visible(self):
        """
        Verified badge unlocks marketplace visibility.
        """
        req = verification_service.create_request(self.coach)
        verification_service.approve_request(req, self.admin)

        self.coach.refresh_from_db()
        self.assertTrue(
            verification_service.can_coach_be_visible(self.coach)
        )

    # --------------------------------------------------
    # QUEUE FLOODING / SCALE STRESS
    # --------------------------------------------------

    def test_queue_stability_under_multiple_requests(self):
        """
        Simulates rapid onboarding of many coaches.
        Ensures admin queue remains correct and deterministic.
        """
        coaches = [
            User.objects.create_user(
                phone=unique_phone(),
                role="coach"
            )
            for _ in range(25)
        ]

        for coach in coaches:
            req = verification_service.create_request(coach)
            verification_service.submit_request(req, coach)

        qs = verification_service.get_pending_requests()
        self.assertEqual(qs.count(), 25)