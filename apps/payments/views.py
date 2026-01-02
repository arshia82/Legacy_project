from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from payments.services.withdrawal import can_withdraw


class WithdrawRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # ✅ ENFORCEMENT (C1C)
        can_withdraw(user)

        # continue withdrawal logic
        # PSP call, balance deduction, etc.

        return Response(
            {"ok": True, "message": "Withdrawal request submitted"},
            status=status.HTTP_200_OK,
        )