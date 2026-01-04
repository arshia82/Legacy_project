from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class TestWebhookReplay(TestCase):
    """
    PURPOSE:
    Block PSP webhook replay attacks.
    BUSINESS RISK:
    Double payouts and accounting fraud.
    """

    def setUp(self):
        self.client = APIClient()

    def test_replay_webhook(self):
        payload = {"ref": "ABC123", "status": "paid"}
        self.client.post(reverse("payment-webhook"), payload)
        res = self.client.post(reverse("payment-webhook"), payload)
        self.assertEqual(res.status_code, 409)