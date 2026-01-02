from django.urls import path
from .views import AdminActionView

urlpatterns = [
    path("admin/actions/", AdminActionView.as_view()),
]