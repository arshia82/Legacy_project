# FILE: myfita/apps/backend/matching/models.py

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class AthletePreferences(models.Model):
    """
    Athlete's preferences for coach matching.
    BP: "athlete enters measurements, goals and training history → 
         MY FITA's AI recommends a shortlist of matched coaches"
    """
    
    class Goal(models.TextChoices):
        WEIGHT_LOSS = "weight_loss", "کاهش وزن"
        MUSCLE_GAIN = "muscle_gain", "افزایش عضله"
        STRENGTH = "strength", "افزایش قدرت"
        ENDURANCE = "endurance", "استقامت"
        FLEXIBILITY = "flexibility", "انعطاف‌پذیری"
        COMPETITION = "competition", "آمادگی مسابقه"
        GENERAL_FITNESS = "general_fitness", "تناسب اندام عمومی"
        REHABILITATION = "rehabilitation", "توانبخشی"
    
    class ExperienceLevel(models.TextChoices):
        BEGINNER = "beginner", "مبتدی (کمتر از ۶ ماه)"
        INTERMEDIATE = "intermediate", "متوسط (۶ ماه تا ۲ سال)"
        ADVANCED = "advanced", "پیشرفته (۲ تا ۵ سال)"
        PROFESSIONAL = "professional", "حرفه‌ای (بیش از ۵ سال)"
    
    class GenderPreference(models.TextChoices):
        MALE = "male", "مرد"
        FEMALE = "female", "زن"
        NO_PREFERENCE = "no_preference", "فرقی نمی‌کند"
    
    class Meta:
        db_table = "matching_athlete_preferences"
        verbose_name = "Athlete Preferences"
        verbose_name_plural = "Athlete Preferences"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matching_preferences"
    )
    
    # Goals (multi-select)
    primary_goal = models.CharField(
        max_length=50,
        choices=Goal.choices,
        default=Goal.GENERAL_FITNESS
    )
    secondary_goals = models.JSONField(default=list, blank=True)
    
    # Experience
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.BEGINNER
    )
    training_days_per_week = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(7)]
    )
    has_gym_access = models.BooleanField(default=True)
    has_home_equipment = models.BooleanField(default=False)
    
    # Physical measurements
    age = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(13), MaxValueValidator(100)]
    )
    height_cm = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(100), MaxValueValidator(250)]
    )
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    target_weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    body_fat_percentage = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True
    )
    
    # Coach preferences
    preferred_coach_gender = models.CharField(
        max_length=20,
        choices=GenderPreference.choices,
        default=GenderPreference.NO_PREFERENCE
    )
    max_budget = models.BigIntegerField(null=True, blank=True)
    preferred_city = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(max_length=50, default="fa")
    
    # Health information
    injuries = models.JSONField(default=list, blank=True)
    medical_conditions = models.JSONField(default=list, blank=True)
    dietary_restrictions = models.JSONField(default=list, blank=True)
    
    # Quiz completion tracking
    quiz_completed = models.BooleanField(default=False)
    quiz_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.athlete}"
    
    @property
    def bmi(self):
        """Calculate BMI if height and weight available"""
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return float(self.weight_kg) / (height_m ** 2)
        return None


class MatchResult(models.Model):
    """
    Stored match results for analytics and caching.
    BP: "AI recommends a shortlist of matched coaches"
    """
    
    class Meta:
        db_table = "matching_match_result"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["athlete", "-score"]),
            models.Index(fields=["coach", "-created_at"]),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="match_results"
    )
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matched_for"
    )
    
    # Scoring
    score = models.DecimalField(max_digits=5, decimal_places=2)
    score_breakdown = models.JSONField(default=dict)
    reasons = models.JSONField(default=list)
    
    # Tracking
    was_viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    was_clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    resulted_in_purchase = models.BooleanField(default=False)
    purchase_at = models.DateTimeField(null=True, blank=True)
    
    # Validity
    is_stale = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Match: {self.athlete} → {self.coach} ({self.score})"
    
    def mark_viewed(self):
        """Mark this match as viewed"""
        from django.utils import timezone
        if not self.was_viewed:
            self.was_viewed = True
            self.viewed_at = timezone.now()
            self.save(update_fields=["was_viewed", "viewed_at"])
    
    def mark_clicked(self):
        """Mark this match as clicked"""
        from django.utils import timezone
        if not self.was_clicked:
            self.was_clicked = True
            self.clicked_at = timezone.now()
            self.save(update_fields=["was_clicked", "clicked_at"])


class MatchingInteraction(models.Model):
    """
    Track user interactions for future ML training.
    BP: "captures structured data... enabling better personalization"
    """
    
    class Action(models.TextChoices):
        VIEW_PROFILE = "view_profile", "View Profile"
        CLICK_PROGRAM = "click_program", "Click Program"
        START_MESSAGE = "start_message", "Start Message"
        PURCHASE = "purchase", "Purchase"
        SKIP = "skip", "Skip"
        SAVE = "save", "Save"
        REPORT = "report", "Report"
    
    class Meta:
        db_table = "matching_interaction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["athlete", "action", "-created_at"]),
            models.Index(fields=["coach", "action", "-created_at"]),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matching_interactions"
    )
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_interactions"
    )
    
    action = models.CharField(max_length=20, choices=Action.choices)
    context = models.JSONField(default=dict, blank=True)
    
    # For ML training
    match_score_at_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=64, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.athlete} → {self.action} → {self.coach}"