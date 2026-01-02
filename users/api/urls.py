# users/api/urls.py

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    OTPSendView,
    OTPVerifyView,
    CoachVerificationView,
    DocumentUploadView,
    # ✅ ADDED: Import missing views for new routes
    VerificationApproveView,
)

app_name = 'users'

urlpatterns = [
    # ... (Your existing paths unchanged) ...
    
    # Coach Verification
    path('verification/', CoachVerificationView.as_view(), name='verification'),
    path('verification/approve/', VerificationApproveView.as_view(), name='verification-approve'),  # ✅ ADDED: For test_admin_approve
    path('verification/document/', DocumentUploadView.as_view(), name='verification-document'),  # ✅ ADDED: For test_upload_document
]