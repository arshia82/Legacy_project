# FILE: myfita/apps/backend/search/models.py

"""
SEARCH MODELS

Models for search analytics, saved searches, and query tracking.
BP: "captures structured data... enabling better personalization"
"""

import uuid
from django.db import models
from django.conf import settings


class SearchQuery(models.Model):
    """
    Track search queries for analytics and autocomplete.
    
    Used to:
    - Power autocomplete suggestions
    - Identify popular searches
    - Improve search relevance over time
    """
    
    class Meta:
        db_table = "search_query"
        verbose_name = "Search Query"
        verbose_name_plural = "Search Queries"
        ordering = ["-search_count", "-last_searched_at"]
        indexes = [
            models.Index(fields=["query_normalized"]),
            models.Index(fields=["-search_count"]),
            models.Index(fields=["category", "-search_count"]),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Query text
    query_text = models.CharField(max_length=255)
    query_normalized = models.CharField(max_length=255, db_index=True)
    
    # Statistics
    search_count = models.PositiveIntegerField(default=1)
    result_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    
    # Categorization
    category = models.CharField(max_length=50, blank=True)  # coach, program, general
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_searched_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.query_text} ({self.search_count} searches)"
    
    @property
    def click_through_rate(self):
        """Calculate click-through rate"""
        if self.search_count == 0:
            return 0
        return round((self.click_count / self.search_count) * 100, 2)


class SearchLog(models.Model):
    """
    Individual search log for detailed analytics.
    
    Tracks each search performed for:
    - User behavior analysis
    - Search quality improvement
    - ML training data collection
    """
    
    class SearchType(models.TextChoices):
        COACH = "coach", "Coach Search"
        PROGRAM = "program", "Program Search"
        GENERAL = "general", "General Search"
    
    class Meta:
        db_table = "search_log"
        verbose_name = "Search Log"
        verbose_name_plural = "Search Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["search_type", "-created_at"]),
            models.Index(fields=["session_id"]),
            models.Index(fields=["-created_at"]),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User (optional for anonymous searches)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_logs"
    )
    
    # Search details
    search_type = models.CharField(
        max_length=20,
        choices=SearchType.choices,
        default=SearchType.GENERAL
    )
    query_text = models.CharField(max_length=255, blank=True)
    filters_applied = models.JSONField(default=dict, blank=True)
    sort_by = models.CharField(max_length=50, blank=True)
    
    # Results
    result_count = models.PositiveIntegerField(default=0)
    result_ids = models.JSONField(default=list, blank=True)  # First N result IDs
    
    # User interaction
    clicked_result_id = models.UUIDField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Session tracking
    session_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Performance
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Search: '{self.query_text}' ({self.result_count} results)"
    
    @property
    def had_click(self):
        return self.clicked_result_id is not None


class SavedSearch(models.Model):
    """
    User's saved search configurations.
    
    Allows users to save filter combinations for quick access.
    """
    
    class Meta:
        db_table = "search_saved"
        verbose_name = "Saved Search"
        verbose_name_plural = "Saved Searches"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_user_saved_search_name"
            )
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_searches"
    )
    
    name = models.CharField(max_length=100)
    search_type = models.CharField(
        max_length=20,
        choices=SearchLog.SearchType.choices,
        default=SearchLog.SearchType.COACH
    )
    
    # Saved configuration
    query_text = models.CharField(max_length=255, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    sort_by = models.CharField(max_length=50, blank=True, default="relevance")
    
    # Notification settings
    notify_new_results = models.BooleanField(default=False)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    last_result_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.user})"