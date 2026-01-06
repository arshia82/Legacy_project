# users/api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from ..models import CoachVerificationRequest
from ..services.verification_service import VerificationService
from ..services.otp_service import send_otp, verify_otp


# ============================================================
# OTP VIEWS
# ============================================================

class RequestOTPView(APIView):
    """Request OTP for phone authentication."""
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone")

        if not phone:
            return Response(
                {"detail": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            send_otp(phone=phone, ip_address=self.get_client_ip(request))
            return Response(
                {"detail": "OTP sent successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


class VerifyOTPView(APIView):
    """Verify OTP and return JWT tokens."""
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone")
        code = request.data.get("code")

        if not phone or not code:
            return Response(
                {"detail": "Phone and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = verify_otp(
                phone=phone,
                code=code,
                ip_address=self.get_client_ip(request),
            )

            if not result:
                return Response(
                    {"detail": "Invalid or expired OTP."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


# ============================================================
# VERIFICATION VIEWS
# ============================================================

class SubmitVerificationRequestAPIView(APIView):
    """Submit coach verification request."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        service = VerificationService(user=request.user)

        try:
            verification_request = service.submit_request()
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "request_number": verification_request.request_number,
                "status": verification_request.status,
            },
            status=status.HTTP_201_CREATED,
        )


class VerificationStatusAPIView(APIView):
    """Get verification request status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            req = CoachVerificationRequest.objects.filter(
                user=request.user
            ).latest("created_at")
        except CoachVerificationRequest.DoesNotExist:
            return Response(
                {"detail": "No verification request found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "request_number": req.request_number,
                "status": req.status,
            }
        )