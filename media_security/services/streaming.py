from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
from coach_profiles.models import CoachMedia
from .signing import verify_signature

def stream_media(request, media_id, token, expires):
    media = CoachMedia.objects.filter(pk=media_id, is_deleted=False).first()
    if not media:
        raise Http404()

    if not verify_signature(media_id, request.user.id, token, expires):
        raise PermissionDenied("Invalid or expired token")

    response = FileResponse(media.file.open("rb"), content_type="image/jpeg")
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response