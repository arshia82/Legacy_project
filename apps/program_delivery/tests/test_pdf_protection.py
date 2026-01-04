from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class TestPDFProtection(TestCase):
    """
    PURPOSE:
    Protect coach IP and athlete privacy.
    BUSINESS RISK:
    Program resale outside platform.
    """

    def setUp(self):
        self.client = APIClient()

    def test_pdf_not_public(self):
        res = self.client.get("/media/programs/sample.pdf")
        self.assertIn(res.status_code, [401, 403])