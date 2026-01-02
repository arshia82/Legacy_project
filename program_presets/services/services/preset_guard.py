from django.core.exceptions import PermissionDenied
from program_presets.models import ProgramPreset


def can_create_preset(*, coach, max_allowed: int):
    count = ProgramPreset.objects.filter(coach=coach).count()

    if count >= max_allowed:
        raise PermissionDenied("Preset limit reached. Upgrade required.")