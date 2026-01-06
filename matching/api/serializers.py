# FILE: myfita/apps/backend/matching/api/serializers.py

from rest_framework import serializers
from matching.models import AthletePreferences, MatchResult, MatchingInteraction


class AthletePreferencesSerializer(serializers.ModelSerializer):
    """Serializer for athlete preferences (quiz)"""
    
    bmi = serializers.ReadOnlyField()
    
    class Meta:
        model = AthletePreferences
        fields = [
            "id",
            "primary_goal",
            "secondary_goals",
            "experience_level",
            "training_days_per_week",
            "has_gym_access",
            "has_home_equipment",
            "age",
            "height_cm",
            "weight_kg",
            "target_weight_kg",
            "body_fat_percentage",
            "bmi",
            "preferred_coach_gender",
            "max_budget",
            "preferred_city",
            "preferred_language",
            "injuries",
            "medical_conditions",
            "dietary_restrictions",
            "quiz_completed",
            "quiz_completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "quiz_completed", "quiz_completed_at", "created_at", "updated_at", "bmi"]
    
    def validate_training_days_per_week(self, value):
        if not 1 <= value <= 7:
            raise serializers.ValidationError("تعداد روزهای تمرین باید بین ۱ تا ۷ باشد.")
        return value
    
    def validate_age(self, value):
        if value and not 13 <= value <= 100:
            raise serializers.ValidationError("سن باید بین ۱۳ تا ۱۰۰ سال باشد.")
        return value


class AthletePreferencesCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating preferences via quiz"""
    
    class Meta:
        model = AthletePreferences
        fields = [
            "primary_goal",
            "secondary_goals",
            "experience_level",
            "training_days_per_week",
            "has_gym_access",
            "has_home_equipment",
            "age",
            "height_cm",
            "weight_kg",
            "target_weight_kg",
            "body_fat_percentage",
            "preferred_coach_gender",
            "max_budget",
            "preferred_city",
            "injuries",
            "medical_conditions",
        ]
    
    def create(self, validated_data):
        from django.utils import timezone
        
        athlete = self.context["request"].user
        validated_data["athlete"] = athlete
        validated_data["quiz_completed"] = True
        validated_data["quiz_completed_at"] = timezone.now()
        
        # Update or create
        instance, created = AthletePreferences.objects.update_or_create(
            athlete=athlete,
            defaults=validated_data
        )
        return instance


class CoachMatchSerializer(serializers.Serializer):
    """Serializer for coach match results"""
    
    coach_id = serializers.UUIDField()
    coach_name = serializers.CharField()
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    reasons = serializers.ListField(child=serializers.CharField())
    score_breakdown = serializers.DictField(required=False)
    specialties = serializers.ListField(child=serializers.CharField())
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_clients = serializers.IntegerField()
    total_programs = serializers.IntegerField()
    price_range_min = serializers.IntegerField()
    price_range_max = serializers.IntegerField()
    city = serializers.CharField(allow_blank=True)
    profile_image = serializers.CharField(allow_null=True)
    is_verified = serializers.BooleanField()
    years_experience = serializers.IntegerField()


class MatchingResultSerializer(serializers.Serializer):
    """Serializer for matching API response"""
    
    success = serializers.BooleanField()
    matches = CoachMatchSerializer(many=True)
    total_coaches_evaluated = serializers.IntegerField()
    preferences_used = serializers.DictField()
    error = serializers.CharField(allow_null=True)


class MatchResultSerializer(serializers.ModelSerializer):
    """Serializer for stored match results"""
    
    coach_name = serializers.CharField(source="coach.get_full_name", read_only=True)
    
    class Meta:
        model = MatchResult
        fields = [
            "id",
            "coach",
            "coach_name",
            "score",
            "reasons",
            "was_viewed",
            "was_clicked",
            "resulted_in_purchase",
            "created_at",
        ]
        read_only_fields = fields


class LogInteractionSerializer(serializers.Serializer):
    """Serializer for logging interactions"""
    
    coach_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=MatchingInteraction.Action.choices)
    context = serializers.DictField(required=False, default=dict)
    session_id = serializers.CharField(required=False, allow_blank=True)