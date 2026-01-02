from django.urls import path
from .views import CoachProfileView, CoachMediaStreamView

urlpatterns = [
    path("coaches/<int:coach_id>/profile/", CoachProfileView.as_view()),
    path("media/<int:media_id>/stream/", CoachMediaStreamView.as_view()),
]