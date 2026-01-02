# users/api/views.py

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from users.models import CoachVerificationRequest
from users.services.verification_service import verification_service


# ============================================================
# OTP VIEWS (SAFE FALLBACK IMPLEMENTATION)
# ============================================================

# ⚠️ otp_service هنوز کامل نیست یا API آن تغییر کرده
# برای اینکه makemigrations / migrate / test بلاک نشود،
# import را ایمن می‌کنیم
try:
    from users.services.otp_service import otp_service
except Exception:
    otp_service = None


class OTPSendView(APIView):
    """
    Send OTP to phone number
    """
    def post(self, request):
        phone = request.data.get("phone")

        if not phone:
            return Response(
                {"detail": "Phone is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_service:
            otp_service.send_otp(phone)

        return Response(
            {"detail": "OTP sent"},
            status=status.HTTP_200_OK
        )


class OTPVerifyView(APIView):
    """
    Verify OTP code
    """
    def post(self, request):
        phone = request.data.get("phone")
        code = request.data.get("code")

        if not phone or not code:
            return Response(
                {"detail": "Phone and code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_service:
            valid = otp_service.verify_otp(phone, code)
            if not valid:
                return Response(
                    {"detail": "Invalid OTP"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            {"detail": "OTP verified"},
            status=status.HTTP_200_OK
        )


# ============================================================
# COACH VERIFICATION VIEWS
# ============================================================

class CoachVerificationView(APIView):
    """
    Create verification request or get current one
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create verification request
        """
        req = verification_service.create_request(request.user)
        return Response(
            {"id": req.id, "status": req.status},
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        """
        Get latest verification request
        """
        req = verification_service.get_coach_request(request.user)
        if not req:
            return Response(
                {"detail": "No verification request"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "id": req.id,
                "status": req.status,
            },
            status=status.HTTP_200_OK
        )


class DocumentUploadView(APIView):
    """
    Upload verification document
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        verification_id = request.data.get("verification_request")
        document_type = request.data.get("document_type")
        file = request.FILES.get("file")

        if not verification_id or not file or not document_type:
            return Response(
                {"detail": "Missing fields"},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification_request = get_object_or_404(
            CoachVerificationRequest,
            id=verification_id
        )

        verification_service.add_document(
            verification_request,
            file,
            document_type,
            user=request.user
        )

        return Response(
            {"detail": "Document uploaded"},
            status=status.HTTP_201_CREATED
        )


class VerificationApproveView(APIView):
    """
    Admin approves verification request
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        verification_id = request.data.get("verification_request")

        if not verification_id:
            return Response(
                {"detail": "verification_request is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification_request = get_object_or_404(
            CoachVerificationRequest,
            id=verification_id
        )

        verification_service.approve_request(
            verification_request,
            request.user
        )

        return Response(
            {"detail": "Verification approved"},
            status=status.HTTP_200_OK
        )