from django.test import TestCase
from django.utils import timezone
from users.models import User
from users.services.verification_service import verification_service, DRAFT, PENDING, APPROVED

class VerificationSecurityTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user(phone="09120000001", role="coach")
        self.admin = User.objects.create_user(phone="09120000002", role="admin", is_staff=True)

    # ---- State machine integrity ----
    def test_create_and_submit_flow(self):
        req = verification_service.create_request(self.coach)
        self.assertEqual(req.status, DRAFT)

        req = verification_service.submit(verification_request=req, actor=self.coach)
        self.assertEqual(req.status, PENDING)

    def test_admin_can_approve_from_any_state(self):
        req = verification_service.create_request(self.coach)
        req = verification_service.approve(verification_request=req, admin=self.admin)
        self.assertEqual(req.status, APPROVED)

    # ---- AuthZ ----
    def test_non_admin_cannot_approve(self):
        req = verification_service.create_request(self.coach)
        with self.assertRaises(Exception):
            verification_service.approve(verification_request=req, admin=self.coach)

    # ---- Queue correctness ----
    def test_admin_queue_lists_pending_only(self):
        req = verification_service.create_request(self.coach)
        verification_service.submit(verification_request=req, actor=self.coach)
        qs = list(verification_service.get_pending_requests())
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].status, PENDING)

    # ---- Marketplace policy ----
    def test_visibility_requires_verified(self):
        self.assertFalse(verification_service.can_be_visible_in_marketplace(self.coach))
        req = verification_service.create_request(self.coach)
        verification_service.approve(verification_request=req, admin=self.admin)
        self.coach.refresh_from_db()
        self.assertTrue(verification_service.can_be_visible_in_marketplace(self.coach))