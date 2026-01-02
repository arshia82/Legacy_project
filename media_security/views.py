from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse

from .services.signing import sign_media_access
from .services.streaming import stream_media

class MediaTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, media_id):
        token_data = sign_media_access(media_id, request.user.id)
        return Response(token_data)

class MediaStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, media_id):
        token = request.query_params.get("token")
        expires = int(request.query_params.get("expires", 0))
        return stream_media(request, media_id, token, expires)