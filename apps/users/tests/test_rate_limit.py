from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class TestGlobalRateLimit(TestCase):
    """
    PURPOSE:
    Enforce platform-wide rate limits.
    BUSINESS RISK:
    Prevents DoS and brute-force attacks.
    """

    def setUp(self):
        self.client = APIClient()

    def test_rate_limit_trigger(self):
        """
        Excessive requests must be throttled.
        """
        for _ in range(100):
            self.client.get(reverse("public-coach-list"))
        res = self.client.get(reverse("public-coach-list"))
        self.assertEqual(res.status_code, 429)