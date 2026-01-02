from django.core.exceptions import PermissionDenied
from programs.models import ProgramPreset

def can_create_preset(coach):
    limit = coach.coachsubscription.package.max_presets
    current = ProgramPreset.objects.filter(coach=coach).count()

    if current >= limit:
        raise PermissionDenied("Upgrade required")