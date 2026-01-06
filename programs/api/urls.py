# FILE: myfita/apps/backend/programs/api/urls.py

from django.urls import path

# Import views here to avoid circular imports (fixes Pylance reportUndefinedVariable)
from .views import ProgramListView

app_name = "programs"

urlpatterns = [
    # Core program endpoints (aligned with Business Plan: "program purchase delivery (PDF)" - page 3)
    path("", ProgramListView.as_view(), name="program-list"),  # List all programs
    # path("<uuid:pk>/", ProgramDetailView.as_view(), name="program-detail"),  # Add later
    
    # Add more as needed - this is minimal to unblock
]