# users/api/urls.py

from django.urls import path

from .views import (
    OTPSendView,
    OTPVerifyView,
    CoachVerificationView,
    DocumentUploadView,
    VerificationApproveView,
    VerificationAdminQueueView,  # ✅ NEW
)

app_name = "users"

urlpatterns = [
    # OTP
    path("otp/send/", OTPSendView.as_view(), name="otp-send"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),

    # Verification
    path("verification/", CoachVerificationView.as_view(), name="verification"),
    path("verification/document/", DocumentUploadView.as_view(), name="verification-document"),
    path("verification/approve/", VerificationApproveView.as_view(), name="verification-approve"),

    # ✅ Admin queue
    path("verification/admin/queue/", VerificationAdminQueueView.as_view(), name="verification-admin-queue"),
]