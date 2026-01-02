import pytest
from django.core.exceptions import PermissionDenied


def test_non_coach_cannot_view_media():
    with pytest.raises(PermissionDenied):
        raise PermissionDenied()