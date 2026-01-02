from django.core.exceptions import PermissionDenied
from .models import CoachMedia


def can_view_media(user, coach_profile):
    """
    Core security rule:
    - Only coaches
    - Only via web (checked at view level)
    """
    if user.role != "coach":
        raise PermissionDenied("Only coaches may view photos.")

    return True


def delete_media(media, requester):
    """
    User-requested deletion after delivery.
    """
    media.is_deleted = True
    media.save(update_fields=["is_deleted"])