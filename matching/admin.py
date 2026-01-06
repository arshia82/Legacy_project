# FILE: myfita/apps/backend/matching/admin.py

from django.contrib import admin
from matching.models import AthletePreferences, MatchResult, MatchingInteraction


@admin.register(AthletePreferences)
class AthletePreferencesAdmin(admin.ModelAdmin):
    list_display = [
        "athlete",
        "primary_goal",
        "experience_level",
        "preferred_city",
        "max_budget",
        "quiz_completed",
        "created_at"
    ]
    list_filter = [
        "primary_goal",
        "experience_level",
        "quiz_completed",
        "has_gym_access"
    ]
    search_fields = ["athlete__phone", "athlete__first_name", "preferred_city"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    fieldsets = (
        ("Athlete", {
            "fields": ("id", "athlete")
        }),
        ("Goals", {
            "fields": ("primary_goal", "secondary_goals")
        }),
        ("Experience", {
            "fields": (
                "experience_level",
                "training_days_per_week",
                "has_gym_access",
                "has_home_equipment"
            )
        }),
        ("Physical", {
            "fields": ("age", "height_cm", "weight_kg", "target_weight_kg", "body_fat_percentage")
        }),
        ("Preferences", {
            "fields": (
                "preferred_coach_gender",
                "max_budget",
                "preferred_city",
                "preferred_language"
            )
        }),
        ("Health", {
            "fields": ("injuries", "medical_conditions", "dietary_restrictions"),
            "classes": ("collapse",)
        }),
        ("Status", {
            "fields": ("quiz_completed", "quiz_completed_at", "created_at", "updated_at")
        }),
    )


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = [
        "athlete",
        "coach",
        "score",
        "was_viewed",
        "was_clicked",
        "resulted_in_purchase",
        "created_at"
    ]
    list_filter = [
        "was_viewed",
        "was_clicked",
        "resulted_in_purchase",
        "is_stale"
    ]
    search_fields = ["athlete__phone", "coach__phone"]
    readonly_fields = ["id", "created_at", "score_breakdown"]
    
    def has_add_permission(self, request):
        return False  # Results are created by the matching service


@admin.register(MatchingInteraction)
class MatchingInteractionAdmin(admin.ModelAdmin):
    list_display = [
        "athlete",
        "coach",
        "action",
        "match_score_at_time",
        "created_at"
    ]
    list_filter = ["action", "created_at"]
    search_fields = ["athlete__phone", "coach__phone", "session_id"]
    readonly_fields = ["id", "created_at"]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False