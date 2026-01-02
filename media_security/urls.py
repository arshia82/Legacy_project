from django.urls import path
from .views import MediaTokenView, MediaStreamView

urlpatterns = [
    path("media/<int:media_id>/token/", MediaTokenView.as_view()),
    path("media/<int:media_id>/stream/", MediaStreamView.as_view()),
]