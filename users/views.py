from django.http import JsonResponse
from django.views import View

from .models import User
from .services.verification_service import VerificationService


class UserStatusView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": "Authentication required"},
                status=401,
            )

        service = VerificationService(user=request.user)

        return JsonResponse(
            {
                "phone": request.user.phone,
                "role": request.user.role,
                "is_verified": request.user.is_verified,
            }
        )