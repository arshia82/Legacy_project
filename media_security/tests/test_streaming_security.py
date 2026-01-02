import pytest
from django.core.exceptions import PermissionDenied

@pytest.mark.django_db
def test_expired_token_denied(client, django_user_model):
    user = django_user_model.objects.create_user(username="c1", password="x", role="coach")
    client.force_login(user)

    response = client.get("/api/media/1/stream/?token=bad&expires=1")
    assert response.status_code in (403, 404)
    