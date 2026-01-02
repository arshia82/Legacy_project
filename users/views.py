# users/api/views.py

from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from users.models import CoachVerificationRequest
from users.services.verification_service import verification_service
from users.services.otp_service import send_otp, verify_otp


# ============================================================
# OTP VIEWS (LOCKED)
# ============================================================

class OTPSendThrottle(UserRateThrottle):
    scope = "otp_send"


class OTPVerifyThrottle(UserRateThrottle):
    scope = "otp_verify"


class OTPSendView(APIView):
    throttle_classes = [OTPSendThrottle]

    def post(self, request):
        phone = request.data.get("phone")
        if not phone:
            return Response({"detail": "Phone is required"}, status=400)

        send_otp(phone, request.META.get("REMOTE_ADDR"))
        return Response({"detail": "OTP sent"}, status=200)


class OTPVerifyView(APIView):
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        phone = request.data.get("phone")
        code = request.data.get("code")

        if not phone or not code:
            return Response({"detail": "Phone and code required"}, status=400)

        result = verify_otp(phone, code, request.META.get("REMOTE_ADDR"))
        if not result:
            return Response({"detail": "Invalid OTP"}, status=400)

        return Response(result, status=200)


# ============================================================
# VERIFICATION VIEWS
# ============================================================

class CoachVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        req = verification_service.create_request(request.user)
        return Response(
            {"id": req.id, "status": req.status},
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        req = verification_service.get_coach_request(request.user)
        if not req:
            return Response({"detail": "No verification request"}, status=404)

        return Response({"id": req.id, "status": req.status})


class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        verification_request = get_object_or_404(
            CoachVerificationRequest,
            id=request.data.get("verification_request")
        )

        verification_service.add_document(
            verification_request,
            request.FILES.get("file"),
            request.data.get("document_type"),
            request.user
        )

        return Response({"detail": "Document uploaded"}, status=201)


class VerificationApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        verification_request = get_object_or_404(
            CoachVerificationRequest,
            id=request.data.get("verification_request")
        )

        verification_service.approve_request(
            verification_request,
            request.user
        )

        return Response({"detail": "Verification approved"}, status=200)


# ✅ NEW: Admin review queue
class VerificationAdminQueueView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = verification_service.admin_pending_queue()
        data = [
            {
                "id": r.id,
                "user": r.user.phone,
                "created_at": r.created_at,
            }
            for r in qs
        ]
        return Response(data)