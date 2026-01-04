from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from users.models import User

class TestAuthSecurity(TestCase):
    """
    PURPOSE:
    Protect authentication flows against impersonation and role abuse.
    BUSINESS RISK:
    Unauthorized access breaks athlete privacy and coach credibility.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="09120000000", password="StrongPass123"
        )

    def test_login_success(self):
        """
        Ensures valid credentials issue JWT.
        """
        res = self.client.post(
            reverse("auth-login"),
            {"phone": "09120000000", "password": "StrongPass123"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_login_wrong_password(self):
        """
        Prevents brute-force success via wrong credentials.
        """
        res = self.client.post(
            reverse("auth-login"),
            {"phone": "09120000000", "password": "wrong"},
        )
        self.assertEqual(res.status_code, 401)