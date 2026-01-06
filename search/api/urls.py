# FILE: myfita/apps/backend/search/api/urls.py

"""
SEARCH API URL ROUTING

All search-related API endpoints.
"""

from django.urls import path
from search.api.views import (
    CoachSearchView,
    ProgramSearchView,
    AutocompleteView,
    FilterOptionsView,
    SavedSearchListView,
    SavedSearchDetailView,
    LogSearchClickView,
    PopularSearchesView,
)

app_name = "search"

urlpatterns = [
    # Main search endpoints
    path(
        "coaches/",
        CoachSearchView.as_view(),
        name="coach-search"
    ),
    path(
        "programs/",
        ProgramSearchView.as_view(),
        name="program-search"
    ),
    
    # Autocomplete
    path(
        "autocomplete/",
        AutocompleteView.as_view(),
        name="autocomplete"
    ),
    
    # Filter options
    path(
        "filters/",
        FilterOptionsView.as_view(),
        name="filter-options"
    ),
    
    # Saved searches
    path(
        "saved/",
        SavedSearchListView.as_view(),
        name="saved-search-list"
    ),
    path(
        "saved/<uuid:pk>/",
        SavedSearchDetailView.as_view(),
        name="saved-search-detail"
    ),
    
    # Analytics
    path(
        "log-click/",
        LogSearchClickView.as_view(),
        name="log-click"
    ),
    path(
        "popular/",
        PopularSearchesView.as_view(),
        name="popular-searches"
    ),
]