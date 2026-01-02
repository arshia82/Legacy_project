from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from users.models import User, CoachVerificationRequest
from users.services.verification_service import verification_service


# ============================================================
# MODEL TESTS
# ============================================================

class VerificationModelTests(TestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000001",
            role="coach"
        )

    def test_status_transitions(self):
        """
        draft -> pending
        """
        req = verification_service.create_request(self.coach)
        self.assertEqual(req.status, "draft")

        file = SimpleUploadedFile(
            "id.jpg",
            b"dummy-content",
            content_type="image/jpeg"
        )

        verification_service.add_document(
            req,
            file,
            document_type="id_card",
            user=self.coach
        )

        verification_service.submit_request(req, self.coach)
        req.refresh_from_db()

        self.assertEqual(req.status, "pending")


# ============================================================
# SERVICE TESTS
# ============================================================

class VerificationServiceTests(TestCase):

    def setUp(self):
        self.coach = User.objects.create_user(
            phone="09120000002",
            role="coach"
        )

        self.athlete = User.objects.create_user(
            phone="09120000003",
            role="athlete"
        )

        self.admin = User.objects.create_user(
            phone="09120000004",
            role="admin",
            is_staff=True
        )

    def test_only_coach_can_create(self):
        with self.assertRaises(Exception):
            verification_service.create_request(self.athlete)

    def test_no_duplicate_active_requests(self):
        verification_service.create_request(self.coach)
        with self.assertRaises(Exception):
            verification_service.create_request(self.coach)

    def test_full_flow(self):
        req = verification_service.create_request(self.coach)
        self.assertEqual(req.status, "draft")

        file = SimpleUploadedFile(
            "cert.pdf",
            b"dummy",
            content_type="application/pdf"
        )

        verification_service.add_document(
            req,
            file,
            document_type="certificate",
            user=self.coach
        )

        verification_service.submit_request(req, self.coach)
        req.refresh_from_db()
        self.assertEqual(req.status, "pending")

        verification_service.approve_request(req, self.admin)
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")
        self.assertTrue(req.user.is_verified)


# ============================================================
# API TESTS
# ============================================================

class VerificationAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.coach = User.objects.create_user(
            phone="09120000005",
            role="coach"
        )

        self.admin = User.objects.create_user(
            phone="09120000006",
            role="admin",
            is_staff=True
        )

    def test_create_verification(self):
        self.client.force_authenticate(self.coach)

        response = self.client.post("/api/auth/verification/")
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)

    def test_upload_document(self):
        self.client.force_authenticate(self.coach)
        req = verification_service.create_request(self.coach)

        file = SimpleUploadedFile(
            "id.jpg",
            b"dummy",
            content_type="image/jpeg"
        )

        response = self.client.post(
            "/api/auth/verification/document/",
            {
                "verification_request": req.id,
                "document_type": "id_card",
                "file": file
            },
            format="multipart"
        )

        self.assertEqual(response.status_code, 201)

    def test_admin_approve(self):
        req = verification_service.create_request(self.coach)

        file = SimpleUploadedFile(
            "id.jpg",
            b"dummy",
            content_type="image/jpeg"
        )

        verification_service.add_document(
            req,
            file,
            "id_card",
            user=self.coach
        )

        verification_service.submit_request(req, self.coach)

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/auth/verification/approve/",
            {"verification_request": req.id}
        )

        self.assertEqual(response.status_code, 200)

        req.refresh_from_db()
        self.assertEqual(req.status, "approved")