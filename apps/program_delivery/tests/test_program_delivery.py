from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

class TestProgramDelivery(TestCase):
    """
    PURPOSE:
    Ensure paid programs are delivered once.
    BUSINESS RISK:
    Duplicate delivery enables sharing & piracy.
    """

    def setUp(self):
        self.client = APIClient()

    def test_single_delivery(self):
        res = self.client.get(reverse("program-delivery", args=[1]))
        self.assertEqual(res.status_code, 200)

    def test_double_delivery_blocked(self):
        self.client.get(reverse("program-delivery", args=[1]))
        res = self.client.get(reverse("program-delivery", args=[1]))
        self.assertEqual(res.status_code, 403)