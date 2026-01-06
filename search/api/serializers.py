# FILE: myfita/apps/backend/search/api/serializers.py

from rest_framework import serializers
from search.models import SearchLog, SavedSearch


class CoachSearchResultSerializer(serializers.Serializer):
    """Serializer for coach search results"""
    
    id = serializers.UUIDField()
    name = serializers.CharField()
    phone = serializers.CharField()
    bio = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    specialties = serializers.ListField(child=serializers.CharField())
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_reviews = serializers.IntegerField()
    total_programs = serializers.IntegerField()
    total_clients = serializers.IntegerField()
    min_price = serializers.IntegerField()
    max_price = serializers.IntegerField()
    profile_image = serializers.CharField(allow_null=True)
    is_verified = serializers.BooleanField()
    years_experience = serializers.IntegerField()
    highlight = serializers.CharField(allow_blank=True)


class ProgramSearchResultSerializer(serializers.Serializer):
    """Serializer for program search results"""
    
    id = serializers.UUIDField()
    title = serializers.CharField()
    short_description = serializers.CharField(allow_blank=True)
    coach_id = serializers.UUIDField(allow_null=True)
    coach_name = serializers.CharField(allow_blank=True)
    category = serializers.CharField()
    difficulty = serializers.CharField()
    price = serializers.IntegerField()
    original_price = serializers.IntegerField(allow_null=True)
    duration_weeks = serializers.IntegerField()
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_reviews = serializers.IntegerField()
    total_purchases = serializers.IntegerField()
    thumbnail = serializers.CharField(allow_null=True)
    is_featured = serializers.BooleanField()
    is_bestseller = serializers.BooleanField()
    discount_percentage = serializers.IntegerField()


class FilterOptionSerializer(serializers.Serializer):
    """Serializer for filter options"""
    
    value = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField(required=False)


class FilterDefinitionSerializer(serializers.Serializer):
    """Serializer for filter definitions"""
    
    name = serializers.CharField()
    label = serializers.CharField()
    type = serializers.CharField()
    options = FilterOptionSerializer(many=True, required=False)
    min_value = serializers.FloatField(allow_null=True, required=False)
    max_value = serializers.FloatField(allow_null=True, required=False)
    step = serializers.FloatField(allow_null=True, required=False)


class SearchResponseSerializer(serializers.Serializer):
    """Serializer for search API response"""
    
    success = serializers.BooleanField()
    results = serializers.ListField()  # Will be CoachSearchResult or ProgramSearchResult
    total_count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    filters_applied = serializers.DictField()
    available_filters = serializers.DictField(required=False)
    suggestions = serializers.ListField(child=serializers.CharField(), required=False)
    search_id = serializers.UUIDField(allow_null=True, required=False)
    error = serializers.CharField(allow_null=True, required=False)


class SearchRequestSerializer(serializers.Serializer):
    """Serializer for search request parameters"""
    
    q = serializers.CharField(required=False, allow_blank=True, default="")
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=50)
    sort_by = serializers.ChoiceField(
        required=False,
        default="relevance",
        choices=[
            ("relevance", "Relevance"),
            ("rating", "Rating"),
            ("price_low", "Price Low"),
            ("price_high", "Price High"),
            ("newest", "Newest"),
            ("popular", "Popular"),
        ]
    )
    
    # Filter fields
    specialty = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    city = serializers.CharField(required=False, allow_blank=True)
    min_rating = serializers.FloatField(required=False, min_value=0, max_value=5)
    min_price = serializers.IntegerField(required=False, min_value=0)
    max_price = serializers.IntegerField(required=False, min_value=0)
    experience_level = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    gender = serializers.CharField(required=False)
    is_verified = serializers.BooleanField(required=False)
    has_availability = serializers.BooleanField(required=False)


class ProgramSearchRequestSerializer(serializers.Serializer):
    """Serializer for program search request"""
    
    q = serializers.CharField(required=False, allow_blank=True, default="")
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=50)
    sort_by = serializers.ChoiceField(
        required=False,
        default="relevance",
        choices=[
            ("relevance", "Relevance"),
            ("rating", "Rating"),
            ("price_low", "Price Low"),
            ("price_high", "Price High"),
            ("newest", "Newest"),
            ("popular", "Popular"),
            ("duration_short", "Duration Short"),
            ("duration_long", "Duration Long"),
        ]
    )
    
    # Filter fields
    category = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    difficulty = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    min_price = serializers.IntegerField(required=False, min_value=0)
    max_price = serializers.IntegerField(required=False, min_value=0)
    min_duration = serializers.IntegerField(required=False, min_value=1)
    max_duration = serializers.IntegerField(required=False, min_value=1)
    min_rating = serializers.FloatField(required=False, min_value=0, max_value=5)
    coach_id = serializers.UUIDField(required=False)
    is_featured = serializers.BooleanField(required=False)
    is_bestseller = serializers.BooleanField(required=False)
    has_discount = serializers.BooleanField(required=False)


class SavedSearchSerializer(serializers.ModelSerializer):
    """Serializer for saved searches"""
    
    class Meta:
        model = SavedSearch
        fields = [
            "id",
            "name",
            "search_type",
            "filters",
            "notify_new_results",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SavedSearchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating saved searches"""
    
    class Meta:
        model = SavedSearch
        fields = [
            "name",
            "search_type",
            "filters",
            "notify_new_results",
        ]
    
    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class AutocompleteResultSerializer(serializers.Serializer):
    """Serializer for autocomplete results"""
    
    text = serializers.CharField()
    type = serializers.CharField()  # "query", "coach", "program"
    id = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)


class LogSearchClickSerializer(serializers.Serializer):
    """Serializer for logging search result clicks"""
    
    search_id = serializers.UUIDField()
    result_id = serializers.UUIDField()
    result_type = serializers.ChoiceField(choices=["coach", "program"])