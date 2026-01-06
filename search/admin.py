# FILE: myfita/apps/backend/search/admin.py

from django.contrib import admin
from search.models import SearchQuery, SearchLog, SavedSearch


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = [
        "query_text",
        "category",
        "search_count",
        "result_count",
        "click_count",
        "last_searched_at"
    ]
    list_filter = ["category", "last_searched_at"]
    search_fields = ["query_text", "query_normalized"]
    readonly_fields = ["id", "created_at", "last_searched_at"]
    ordering = ["-search_count"]


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = [
        "query_text",
        "search_type",
        "user",
        "result_count",
        "clicked_result_id",
        "created_at"
    ]
    list_filter = ["search_type", "created_at"]
    search_fields = ["query_text", "user__phone"]
    readonly_fields = ["id", "created_at", "result_ids"]
    ordering = ["-created_at"]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "user",
        "search_type",
        "notify_new_results",
        "created_at"
    ]
    list_filter = ["search_type", "notify_new_results", "created_at"]
    search_fields = ["name", "user__phone"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]