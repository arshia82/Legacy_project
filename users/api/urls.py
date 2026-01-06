# users/api/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RequestOTPView,
    VerifyOTPView,
    SubmitVerificationRequestAPIView,
    VerificationStatusAPIView,
)

app_name = "users"

urlpatterns = [
    # OTP Authentication
    path("otp/request/", RequestOTPView.as_view(), name="otp-request"),
    path("otp/verify/", VerifyOTPView.as_view(), name="otp-verify"),

    # Token refresh
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Coach Verification
    path("verification/submit/", SubmitVerificationRequestAPIView.as_view(), name="verification-submit"),
    path("verification/status/", VerificationStatusAPIView.as_view(), name="verification-status"),
]