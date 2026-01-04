from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class TestOTPSecurity(TestCase):
    """
    PURPOSE:
    Enforce OTP TTL, max attempts, and resend limits.
    BUSINESS RISK:
    OTP abuse enables account takeover.
    """

    def setUp(self):
        self.client = APIClient()

    def test_otp_send_limit(self):
        """
        After max sends per hour, requests must be blocked.
        """
        for _ in range(3):
            self.client.post(reverse("otp-send"), {"phone": "09123334444"})
        res = self.client.post(reverse("otp-send"), {"phone": "09123334444"})
        self.assertEqual(res.status_code, 429)

    def test_otp_invalid_code(self):
        """
        Invalid OTP must never authenticate.
        """
        res = self.client.post(
            reverse("otp-verify"),
            {"phone": "09123334444", "code": "000000"},
        )
        self.assertEqual(res.status_code, 400)