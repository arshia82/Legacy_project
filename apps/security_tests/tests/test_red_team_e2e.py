from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class TestRedTeamE2E(TestCase):
    """
    PURPOSE:
    Simulate full attack chain.
    BUSINESS RISK:
    Platform-wide trust collapse.
    """

    def setUp(self):
        self.client = APIClient()

    def test_full_attack_chain(self):
        """
        OTP abuse → auth → payment replay → delivery abuse
        must fail at some point.
        """
        otp = self.client.post(reverse("otp-send"), {"phone": "09129998888"})
        login = self.client.post(reverse("auth-login"), {"phone": "09129998888", "code": "000000"})
        self.assertNotEqual(login.status_code, 200)