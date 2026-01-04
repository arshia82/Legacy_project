from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from users.models import User

class TestCoachVerification(TestCase):
    """
    PURPOSE:
    Validate coach verification lifecycle.
    BUSINESS RISK:
    Fake coaches destroy trust and brand.
    """

    def setUp(self):
        self.client = APIClient()
        self.coach = User.objects.create_user(
            phone="09121111111", password="Pass1234", is_coach=True
        )
        self.client.force_authenticate(self.coach)

    def test_create_verification_request(self):
        """
        Coach can submit verification request.
        """
        res = self.client.post(reverse("verification-create"))
        self.assertEqual(res.status_code, 201)

    def test_no_duplicate_active_requests(self):
        """
        Only one active verification request allowed.
        """
        self.client.post(reverse("verification-create"))
        res = self.client.post(reverse("verification-create"))
        self.assertEqual(res.status_code, 400)