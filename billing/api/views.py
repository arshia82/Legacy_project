# billing/api/views.py
import uuid
from datetime import date, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from ..services.trust_token_service import TrustTokenService
from ..services.payout_service import PayoutService
from ..services.audit_service import AuditService


class CreateTrustTokenView(APIView):
    """Create a trust token for a program purchase."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        required_fields = ["program_id", "coach_id", "gross_amount", "idempotency_key"]
        
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {"detail": f"{field} is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            program_id = uuid.UUID(request.data["program_id"])
            coach_id = uuid.UUID(request.data["coach_id"])
            gross_amount = int(request.data["gross_amount"])
            idempotency_key = request.data["idempotency_key"]
        except (ValueError, TypeError) as e:
            return Response(
                {"detail": f"Invalid data: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = TrustTokenService()
        token = service.create_token(
            program_id=program_id,
            coach_id=coach_id,
            athlete_id=request.user.id,
            gross_amount=gross_amount,
            idempotency_key=idempotency_key,
            ip_address=self._get_client_ip(request),
        )

        return Response({
            "token_id": str(token.id),
            "gross_amount": token.gross_amount,
            "commission_amount": token.commission_amount,
            "net_amount": token.net_amount,
            "commission_rate": str(token.commission_rate),
            "expires_at": token.expires_at.isoformat(),
        }, status=status.HTTP_201_CREATED)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


class ValidateTokenView(APIView):
    """Validate a trust token."""
    permission_classes = [IsAuthenticated]

    def get(self, request, token_id):
        service = TrustTokenService()
        is_valid, error, token = service.validate_token(token_id)

        if not is_valid:
            return Response(
                {"valid": False, "error": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "valid": True,
            "token_id": str(token.id),
            "gross_amount": token.gross_amount,
            "commission_amount": token.commission_amount,
            "net_amount": token.net_amount,
            "status": token.status,
        })


class CreatePayoutView(APIView):
    """Create a payout from a trust token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token_id = request.data.get("token_id")
        if not token_id:
            return Response(
                {"detail": "token_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token_uuid = uuid.UUID(token_id)
        except ValueError:
            return Response(
                {"detail": "Invalid token_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = PayoutService()
        success, error, payout = service.create_payout(
            token_id=token_uuid,
            coach=request.user,
            ip_address=self._get_client_ip(request),
        )

        if not success:
            return Response(
                {"detail": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "payout_id": str(payout.id),
            "status": payout.status,
            "gross_amount": payout.gross_amount,
            "commission_amount": payout.commission_amount,
            "net_amount": payout.net_amount,
        }, status=status.HTTP_201_CREATED)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


class PayoutStatusView(APIView):
    """Get payout status."""
    permission_classes = [IsAuthenticated]

    def get(self, request, payout_id):
        from ..models import Payout

        try:
            payout = Payout.objects.get(id=payout_id, coach=request.user)
        except Payout.DoesNotExist:
            return Response(
                {"detail": "Payout not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "payout_id": str(payout.id),
            "status": payout.status,
            "gross_amount": payout.gross_amount,
            "commission_amount": payout.commission_amount,
            "net_amount": payout.net_amount,
            "created_at": payout.created_at.isoformat(),
            "completed_at": payout.completed_at.isoformat() if payout.completed_at else None,
        })


class CommissionSummaryView(APIView):
    """Get commission summary for CFO."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        try:
            if start_date_str:
                start_date = date.fromisoformat(start_date_str)
            else:
                start_date = date.today() - timedelta(days=30)

            if end_date_str:
                end_date = date.fromisoformat(end_date_str)
            else:
                end_date = date.today()
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = AuditService()
        summary = service.get_commission_summary(start_date, end_date)

        return Response(summary)