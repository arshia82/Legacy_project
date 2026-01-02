from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import CoachProfile, CoachMedia
from .serializers import (
    CoachProfilePublicSerializer,
    CoachProfilePrivateSerializer,
)
from .permissions import IsCoach
from .services import can_view_media


class CoachProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, coach_id):
        profile = CoachProfile.objects.get(pk=coach_id)

        if request.user.role == "coach":
            serializer = CoachProfilePrivateSerializer(profile)
        else:
            serializer = CoachProfilePublicSerializer(profile)

        return Response(serializer.data)


class CoachMediaStreamView(APIView):
    permission_classes = [IsAuthenticated, IsCoach]

    def get(self, request, media_id):
        media = CoachMedia.objects.get(pk=media_id, is_deleted=False)
        can_view_media(request.user, media.profile)

        response = Response(media.file.read(), content_type="image/jpeg")
        response["Cache-Control"] = "no-store"
        return response