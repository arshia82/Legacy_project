from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class TestPaymentSecurity(TestCase):
    """
    PURPOSE:
    Protect commission and GMV integrity.
    BUSINESS RISK:
    Revenue leakage undermines business model (12% take rate).
    """

    def setUp(self):
        self.client = APIClient()

    def test_price_tampering(self):
        """
        Client-side price manipulation must fail.
        """
        res = self.client.post(
            reverse("payment-init"),
            {"program_id": 1, "price": 1000},
        )
        self.assertEqual(res.status_code, 400)