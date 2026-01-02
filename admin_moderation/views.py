from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .models import AdminAction

class AdminActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        AdminAction.objects.create(
            admin=request.user,
            action=request.data["action"],
            target_id=request.data["target_id"],
            reason=request.data.get("reason", "")
        )
        return Response({"status": "ok"})