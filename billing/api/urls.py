# billing/api/urls.py
from django.urls import path

from .views import (
    CreateTrustTokenView,
    ValidateTokenView,
    CreatePayoutView,
    PayoutStatusView,
    CommissionSummaryView,
)

app_name = "billing"

urlpatterns = [
    # Trust tokens
    path("tokens/create/", CreateTrustTokenView.as_view(), name="token-create"),
    path("tokens/validate/<uuid:token_id>/", ValidateTokenView.as_view(), name="token-validate"),
    
    # Payouts
    path("payouts/create/", CreatePayoutView.as_view(), name="payout-create"),
    path("payouts/<uuid:payout_id>/status/", PayoutStatusView.as_view(), name="payout-status"),
    
    # Admin/CFO
    path("admin/commission-summary/", CommissionSummaryView.as_view(), name="commission-summary"),
]