# FILE: myfita/apps/backend/matching/api/urls.py

from django.urls import path
from matching.api.views import (
    AthletePreferencesView,
    CoachMatchingView,
    MatchHistoryView,
    LogInteractionView,
)

app_name = "matching"

urlpatterns = [
    # Quiz / Preferences
    path(
        "preferences/",
        AthletePreferencesView.as_view(),
        name="preferences"
    ),
    
    # Matching
    path(
        "coaches/",
        CoachMatchingView.as_view(),
        name="match-coaches"
    ),
    
    # History
    path(
        "history/",
        MatchHistoryView.as_view(),
        name="match-history"
    ),
    
    # Interaction logging
    path(
        "log-interaction/",
        LogInteractionView.as_view(),
        name="log-interaction"
    ),
]