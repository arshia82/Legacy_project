# FILE: myfita/apps/backend/matching/services/matching_service.py

import uuid
from decimal import Decimal
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from django.db.models import Q, Avg, Count, F
from django.utils import timezone

from users.models import User
from matching.models import AthletePreferences, MatchResult, MatchingInteraction


@dataclass
class CoachMatch:
    """Individual coach match result"""
    coach_id: uuid.UUID
    coach_name: str
    score: Decimal
    reasons: List[str] = field(default_factory=list)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    specialties: List[str] = field(default_factory=list)
    avg_rating: Decimal = Decimal("0.00")
    total_clients: int = 0
    total_programs: int = 0
    price_range_min: int = 0
    price_range_max: int = 0
    city: str = ""
    profile_image: Optional[str] = None
    is_verified: bool = False
    years_experience: int = 0


@dataclass
class MatchingResult:
    """Result of matching operation"""
    success: bool
    matches: List[CoachMatch] = field(default_factory=list)
    total_coaches_evaluated: int = 0
    preferences_used: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class CoachMatchingService:
    """
    Rule-based coach matching service (Phase 1 - No ML).
    
    BP: "AI recommends a shortlist of matched coaches... 
         reduces time to first purchase"
    
    BP Risk Mitigation: "AI Dependency Cold start Cost Risk - AI promised before data exists"
    Solution: Deterministic rules that work with ZERO training data while collecting
    interaction data for future ML models.
    
    Scoring Weights (Total: 100 points):
    - Specialty/Goal Match: 35 points
    - Location Match: 20 points
    - Price Fit: 15 points
    - Experience Level Match: 10 points
    - Rating & Reviews: 10 points
    - Availability/Activity: 5 points
    - Gender Preference: 5 points
    """
    
    # Scoring weights
    WEIGHT_SPECIALTY = 35
    WEIGHT_LOCATION = 20
    WEIGHT_PRICE = 15
    WEIGHT_EXPERIENCE = 10
    WEIGHT_RATING = 10
    WEIGHT_ACTIVITY = 5
    WEIGHT_GENDER = 5
    
    # Goal to specialty mapping (Persian keywords)
    GOAL_SPECIALTY_MAP = {
        "weight_loss": ["کاهش وزن", "چربی‌سوزی", "لاغری", "رژیم", "کاردیو", "weight_loss", "fat_burn"],
        "muscle_gain": ["بدنسازی", "عضله‌سازی", "هایپرتروفی", "حجم", "bodybuilding", "muscle", "hypertrophy"],
        "strength": ["قدرتی", "پاورلیفتینگ", "وزنه‌برداری", "powerlifting", "strength"],
        "endurance": ["استقامت", "کاردیو", "دویدن", "کراس‌فیت", "cardio", "endurance", "crossfit"],
        "flexibility": ["یوگا", "انعطاف", "کششی", "پیلاتس", "yoga", "flexibility", "pilates"],
        "competition": ["مسابقات", "پرورش اندام", "آمادگی مسابقه", "competition", "contest_prep"],
        "general_fitness": ["تناسب اندام", "سلامت", "عمومی", "fitness", "general", "wellness"],
        "rehabilitation": ["توانبخشی", "آسیب", "فیزیوتراپی", "rehab", "injury", "recovery"],
    }
    
    # Experience level compatibility matrix
    EXPERIENCE_COMPATIBILITY = {
        "beginner": {"beginner": 1.0, "intermediate": 0.8, "advanced": 0.4, "professional": 0.2},
        "intermediate": {"beginner": 0.6, "intermediate": 1.0, "advanced": 0.9, "professional": 0.5},
        "advanced": {"beginner": 0.3, "intermediate": 0.7, "advanced": 1.0, "professional": 0.9},
        "professional": {"beginner": 0.2, "intermediate": 0.4, "advanced": 0.8, "professional": 1.0},
    }
    
    def match_coaches(
        self,
        athlete_id: uuid.UUID,
        limit: int = 10,
        force_refresh: bool = False
    ) -> MatchingResult:
        """
        Find best matching coaches for an athlete.
        
        Args:
            athlete_id: UUID of athlete
            limit: Maximum number of matches to return
            force_refresh: If True, recalculate even if recent results exist
            
        Returns:
            MatchingResult with ranked coach matches
        """
        
        # Get athlete preferences
        try:
            preferences = AthletePreferences.objects.get(athlete_id=athlete_id)
        except AthletePreferences.DoesNotExist:
            return MatchingResult(
                success=False,
                error="لطفاً ابتدا پرسشنامه تطبیق را تکمیل کنید."
            )
        
        # Check for recent cached results (within 1 hour)
        if not force_refresh:
            recent_cutoff = timezone.now() - timezone.timedelta(hours=1)
            cached = MatchResult.objects.filter(
                athlete_id=athlete_id,
                created_at__gte=recent_cutoff,
                is_stale=False
            ).order_by("-score")[:limit]
            
            if cached.exists():
                return self._build_result_from_cache(cached, preferences)
        
        # Get verified, active coaches
        coaches = User.objects.filter(
            role="coach",
            is_active=True
        ).exclude(
            id=athlete_id  # Cannot match with self
        ).prefetch_related("programs")
        
        # Score each coach
        scored_coaches = []
        for coach in coaches:
            score, breakdown, reasons = self._calculate_match_score(preferences, coach)
            
            if score > 0:
                scored_coaches.append({
                    "coach": coach,
                    "score": score,
                    "breakdown": breakdown,
                    "reasons": reasons
                })
        
        # Sort by score descending
        scored_coaches.sort(key=lambda x: x["score"], reverse=True)
        
        # Take top matches
        top_matches = scored_coaches[:limit]
        
        # Build result and store for analytics
        matches = []
        for item in top_matches:
            coach = item["coach"]
            match = self._build_coach_match(coach, item)
            matches.append(match)
            
            # Store match result
            MatchResult.objects.update_or_create(
                athlete_id=athlete_id,
                coach=coach,
                defaults={
                    "score": match.score,
                    "score_breakdown": item["breakdown"],
                    "reasons": item["reasons"],
                    "is_stale": False
                }
            )
        
        # Mark old results as stale
        MatchResult.objects.filter(
            athlete_id=athlete_id
        ).exclude(
            coach_id__in=[m.coach_id for m in matches]
        ).update(is_stale=True)
        
        return MatchingResult(
            success=True,
            matches=matches,
            total_coaches_evaluated=len(coaches),
            preferences_used={
                "primary_goal": preferences.primary_goal,
                "experience_level": preferences.experience_level,
                "preferred_city": preferences.preferred_city,
                "max_budget": preferences.max_budget,
            }
        )
    
    def _calculate_match_score(
        self,
        preferences: AthletePreferences,
        coach
    ) -> tuple:
        """
        Calculate match score between athlete preferences and coach.
        
        Returns:
            Tuple of (score: float, breakdown: dict, reasons: List[str])
        """
        breakdown = {}
        reasons = []
        
        # 1. Specialty/Goal Match (35 points)
        specialty_score, specialty_reason = self._score_specialty_match(preferences, coach)
        breakdown["specialty"] = specialty_score
        if specialty_reason:
            reasons.append(specialty_reason)
        
        # 2. Location Match (20 points)
        location_score, location_reason = self._score_location_match(preferences, coach)
        breakdown["location"] = location_score
        if location_reason:
            reasons.append(location_reason)
        
        # 3. Price Fit (15 points)
        price_score, price_reason = self._score_price_fit(preferences, coach)
        breakdown["price"] = price_score
        if price_reason:
            reasons.append(price_reason)
        
        # 4. Experience Level Match (10 points)
        exp_score, exp_reason = self._score_experience_match(preferences, coach)
        breakdown["experience"] = exp_score
        if exp_reason:
            reasons.append(exp_reason)
        
        # 5. Rating & Reviews (10 points)
        rating_score, rating_reason = self._score_rating(coach)
        breakdown["rating"] = rating_score
        if rating_reason:
            reasons.append(rating_reason)
        
        # 6. Activity/Availability (5 points)
        activity_score = self._score_activity(coach)
        breakdown["activity"] = activity_score
        
        # 7. Gender Preference (5 points)
        gender_score = self._score_gender_preference(preferences, coach)
        breakdown["gender"] = gender_score
        
        total_score = sum(breakdown.values())
        
        return total_score, breakdown, reasons
    
    def _score_specialty_match(
        self,
        preferences: AthletePreferences,
        coach
    ) -> tuple:
        """Score based on goal-specialty alignment"""
        
        coach_specialties = getattr(coach, "specialties", []) or []
        coach_bio = getattr(coach, "bio", "") or ""
        
        if not coach_specialties and not coach_bio:
            return self.WEIGHT_SPECIALTY * 0.3, None
        
        # Combine specialties and bio for matching
        coach_keywords = set(s.lower() for s in coach_specialties)
        coach_keywords.update(coach_bio.lower().split())
        
        # Get relevant keywords for athlete's goal
        target_keywords = set(
            k.lower() for k in self.GOAL_SPECIALTY_MAP.get(preferences.primary_goal, [])
        )
        
        # Check for overlap
        matching = coach_keywords & target_keywords
        
        if matching:
            goal_display = dict(AthletePreferences.Goal.choices).get(
                preferences.primary_goal, preferences.primary_goal
            )
            return self.WEIGHT_SPECIALTY, f"متخصص {goal_display}"
        
        # Check secondary goals
        for secondary in (preferences.secondary_goals or []):
            target = set(k.lower() for k in self.GOAL_SPECIALTY_MAP.get(secondary, []))
            if coach_keywords & target:
                return self.WEIGHT_SPECIALTY * 0.6, "مرتبط با اهداف شما"
        
        return self.WEIGHT_SPECIALTY * 0.2, None
    
    def _score_location_match(
        self,
        preferences: AthletePreferences,
        coach
    ) -> tuple:
        """Score based on location proximity"""
        
        if not preferences.preferred_city:
            return self.WEIGHT_LOCATION * 0.5, None
        
        coach_city = getattr(coach, "city", "") or ""
        
        if coach_city and coach_city.lower().strip() == preferences.preferred_city.lower().strip():
            return self.WEIGHT_LOCATION, f"در {coach_city}"
        
        # Province-level matching could be added here
        return self.WEIGHT_LOCATION * 0.2, None
    
    def _score_price_fit(
        self,
        preferences: AthletePreferences,
        coach
    ) -> tuple:
        """Score based on price range fit"""
        
        if not preferences.max_budget:
            return self.WEIGHT_PRICE * 0.5, None
        
        # Get coach's program prices
        programs = coach.programs.filter(status="published") if hasattr(coach, "programs") else []
        
        if not programs:
            return self.WEIGHT_PRICE * 0.3, None
        
        min_price = min(p.price for p in programs)
        
        if min_price <= preferences.max_budget:
            return self.WEIGHT_PRICE, "در محدوده بودجه شما"
        
        # Within 20% over budget
        if min_price <= preferences.max_budget * 1.2:
            return self.WEIGHT_PRICE * 0.5, "نزدیک به بودجه شما"
        
        return 0, None
    
    def _score_experience_match(
        self,
        preferences: AthletePreferences,
        coach
    ) -> tuple:
        """Score based on experience level compatibility"""
        
        coach_target_levels = getattr(coach, "target_experience_levels", []) or []
        
        if not coach_target_levels:
            return self.WEIGHT_EXPERIENCE * 0.5, None
        
        # Get compatibility score
        athlete_level = preferences.experience_level
        best_match = 0
        
        for coach_level in coach_target_levels:
            compat = self.EXPERIENCE_COMPATIBILITY.get(athlete_level, {}).get(coach_level, 0)
            best_match = max(best_match, compat)
        
        if best_match >= 0.8:
            level_display = dict(AthletePreferences.ExperienceLevel.choices).get(
                athlete_level, athlete_level
            )
            return self.WEIGHT_EXPERIENCE * best_match, f"مناسب سطح {level_display}"
        
        return self.WEIGHT_EXPERIENCE * best_match, None
    
    def _score_rating(self, coach) -> tuple:
        """Score based on coach rating"""
        
        avg_rating = getattr(coach, "avg_rating", None)
        review_count = getattr(coach, "total_reviews", 0) or 0
        
        if not avg_rating or review_count < 3:
            return self.WEIGHT_RATING * 0.3, None
        
        if avg_rating >= 4.5:
            return self.WEIGHT_RATING, f"⭐ {avg_rating}"
        elif avg_rating >= 4.0:
            return self.WEIGHT_RATING * 0.8, f"⭐ {avg_rating}"
        elif avg_rating >= 3.5:
            return self.WEIGHT_RATING * 0.5, None
        
        return self.WEIGHT_RATING * 0.2, None
    
    def _score_activity(self, coach) -> float:
        """Score based on recent activity"""
        
        last_login = getattr(coach, "last_login", None)
        
        if not last_login:
            return self.WEIGHT_ACTIVITY * 0.3
        
        days_since_login = (timezone.now() - last_login).days
        
        if days_since_login <= 1:
            return self.WEIGHT_ACTIVITY
        elif days_since_login <= 7:
            return self.WEIGHT_ACTIVITY * 0.8
        elif days_since_login <= 30:
            return self.WEIGHT_ACTIVITY * 0.5
        
        return self.WEIGHT_ACTIVITY * 0.2
    
    def _score_gender_preference(
        self,
        preferences: AthletePreferences,
        coach
    ) -> float:
        """Score based on gender preference"""
        
        if preferences.preferred_coach_gender == "no_preference":
            return self.WEIGHT_GENDER
        
        coach_gender = getattr(coach, "gender", None)
        
        if not coach_gender:
            return self.WEIGHT_GENDER * 0.5
        
        if coach_gender == preferences.preferred_coach_gender:
            return self.WEIGHT_GENDER
        
        return 0
    
    def _build_coach_match(self, coach, item: dict) -> CoachMatch:
        """Build CoachMatch object from coach and scoring data"""
        
        # Get program stats
        programs = list(coach.programs.filter(status="published")) if hasattr(coach, "programs") else []
        
        price_min = min((p.price for p in programs), default=0)
        price_max = max((p.price for p in programs), default=0)
        
        return CoachMatch(
            coach_id=coach.id,
            coach_name=coach.get_full_name() or coach.phone,
            score=Decimal(str(round(item["score"], 2))),
            reasons=item["reasons"],
            score_breakdown=item["breakdown"],
            specialties=getattr(coach, "specialties", []) or [],
            avg_rating=Decimal(str(getattr(coach, "avg_rating", 0) or 0)),
            total_clients=getattr(coach, "total_clients", 0) or 0,
            total_programs=len(programs),
            price_range_min=price_min,
            price_range_max=price_max,
            city=getattr(coach, "city", "") or "",
            profile_image=coach.profile_image.url if hasattr(coach, "profile_image") and coach.profile_image else None,
            is_verified=getattr(coach, "is_verified", False),
            years_experience=getattr(coach, "years_experience", 0) or 0
        )
    
    def _build_result_from_cache(
        self,
        cached_results,
        preferences: AthletePreferences
    ) -> MatchingResult:
        """Build MatchingResult from cached MatchResult objects"""
        
        matches = []
        for result in cached_results:
            coach = result.coach
            matches.append(CoachMatch(
                coach_id=coach.id,
                coach_name=coach.get_full_name() or coach.phone,
                score=result.score,
                reasons=result.reasons,
                score_breakdown=result.score_breakdown,
                specialties=getattr(coach, "specialties", []) or [],
                avg_rating=Decimal(str(getattr(coach, "avg_rating", 0) or 0)),
                total_clients=getattr(coach, "total_clients", 0) or 0,
                total_programs=coach.programs.filter(status="published").count() if hasattr(coach, "programs") else 0,
                city=getattr(coach, "city", "") or "",
                is_verified=getattr(coach, "is_verified", False)
            ))
        
        return MatchingResult(
            success=True,
            matches=matches,
            preferences_used={
                "primary_goal": preferences.primary_goal,
                "experience_level": preferences.experience_level,
            }
        )
    
    def log_interaction(
        self,
        athlete_id: uuid.UUID,
        coach_id: uuid.UUID,
        action: str,
        context: dict = None,
        session_id: str = None
    ) -> MatchingInteraction:
        """
        Log an interaction for ML training data collection.
        
        BP: "captures structured data... enabling better personalization"
        """
        
        # Get current match score if exists
        match_score = None
        try:
            match_result = MatchResult.objects.get(
                athlete_id=athlete_id,
                coach_id=coach_id,
                is_stale=False
            )
            match_score = match_result.score
        except MatchResult.DoesNotExist:
            pass
        
        interaction = MatchingInteraction.objects.create(
            athlete_id=athlete_id,
            coach_id=coach_id,
            action=action,
            context=context or {},
            match_score_at_time=match_score,
            session_id=session_id or ""
        )
        
        # Update match result tracking
        if action == MatchingInteraction.Action.VIEW_PROFILE:
            MatchResult.objects.filter(
                athlete_id=athlete_id,
                coach_id=coach_id
            ).update(was_viewed=True, viewed_at=timezone.now())
        
        elif action == MatchingInteraction.Action.CLICK_PROGRAM:
            MatchResult.objects.filter(
                athlete_id=athlete_id,
                coach_id=coach_id
            ).update(was_clicked=True, clicked_at=timezone.now())
        
        elif action == MatchingInteraction.Action.PURCHASE:
            MatchResult.objects.filter(
                athlete_id=athlete_id,
                coach_id=coach_id
            ).update(resulted_in_purchase=True, purchase_at=timezone.now())
        
        return interaction