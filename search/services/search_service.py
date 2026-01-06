# FILE: myfita/apps/backend/search/services/search_service.py

"""
COACH & PROGRAM SEARCH SERVICE

BP: "search filter" for coach discovery
BP: "coach athlete profiles, search filter, program purchase delivery"

Features:
- Full-text search with Persian support
- Multi-filter support (specialty, city, price, rating, etc.)
- Search analytics and logging
- Autocomplete suggestions
- Result ranking
"""

import uuid
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from decimal import Decimal
from django.db.models import Q, F, Count, Avg, Min, Max
from django.db.models.functions import Coalesce
from django.utils import timezone

from users.models import User
from programs.models import Program
from search.models import SearchQuery, SearchLog


@dataclass
class CoachSearchResult:
    """Individual coach search result"""
    id: uuid.UUID
    name: str
    phone: str
    bio: str = ""
    city: str = ""
    specialties: List[str] = field(default_factory=list)
    avg_rating: Decimal = Decimal("0.00")
    total_reviews: int = 0
    total_programs: int = 0
    total_clients: int = 0
    min_price: int = 0
    max_price: int = 0
    profile_image: Optional[str] = None
    is_verified: bool = False
    years_experience: int = 0
    highlight: str = ""


@dataclass
class ProgramSearchResult:
    """Individual program search result"""
    id: uuid.UUID
    title: str
    short_description: str = ""
    coach_id: uuid.UUID = None
    coach_name: str = ""
    category: str = ""
    difficulty: str = ""
    price: int = 0
    original_price: Optional[int] = None
    duration_weeks: int = 0
    avg_rating: Decimal = Decimal("0.00")
    total_reviews: int = 0
    total_purchases: int = 0
    thumbnail: Optional[str] = None
    is_featured: bool = False
    is_bestseller: bool = False
    discount_percentage: int = 0


@dataclass
class SearchResponse:
    """Search API response"""
    success: bool
    results: List[Any] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    available_filters: Dict[str, List] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    search_id: Optional[uuid.UUID] = None
    error: Optional[str] = None


class CoachSearchService:
    """
    Service for searching and filtering coaches.
    
    BP: "search filter" for coach discovery
    """
    
    # Searchable text fields
    SEARCH_FIELDS = ["first_name", "last_name", "bio", "city"]
    
    # Available filter definitions
    AVAILABLE_FILTERS = {
        "specialty": {
            "type": "multi_select",
            "options": [
                ("weight_loss", "کاهش وزن"),
                ("muscle_gain", "عضله‌سازی"),
                ("strength", "قدرتی"),
                ("bodybuilding", "بدنسازی"),
                ("powerlifting", "پاورلیفتینگ"),
                ("crossfit", "کراسفیت"),
                ("nutrition", "تغذیه"),
                ("competition_prep", "آمادگی مسابقه"),
                ("rehabilitation", "توانبخشی"),
            ]
        },
        "city": {
            "type": "select",
            "options": []  # Populated dynamically
        },
        "min_rating": {
            "type": "range",
            "min": 0,
            "max": 5,
            "step": 0.5
        },
        "price_range": {
            "type": "range",
            "min": 0,
            "max": 10000000
        },
        "experience_level": {
            "type": "multi_select",
            "options": [
                ("beginner", "مناسب مبتدی"),
                ("intermediate", "مناسب متوسط"),
                ("advanced", "مناسب پیشرفته"),
                ("professional", "مناسب حرفه‌ای"),
            ]
        },
        "gender": {
            "type": "select",
            "options": [
                ("male", "مرد"),
                ("female", "زن"),
            ]
        },
        "is_verified": {
            "type": "boolean"
        },
        "has_availability": {
            "type": "boolean"
        },
    }
    
    def search(
        self,
        query: str = "",
        filters: Dict[str, Any] = None,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 20,
        user_id: uuid.UUID = None,
        session_id: str = None,
        ip_address: str = None
    ) -> SearchResponse:
        """
        Search for coaches with optional filters.
        
        Args:
            query: Search query text
            filters: Dict of filter name to value
            sort_by: Sort option (relevance, rating, price_low, price_high, newest)
            page: Page number (1-indexed)
            page_size: Results per page (max 50)
            user_id: Optional user ID for logging
            session_id: Optional session ID for logging
            ip_address: Optional IP for logging
            
        Returns:
            SearchResponse with results and metadata
        """
        
        filters = filters or {}
        page_size = min(page_size, 50)
        
        # Base queryset - active coaches only
        queryset = User.objects.filter(
            role="coach",
            is_active=True
        ).annotate(
            program_count=Count("coach_programs", filter=Q(coach_programs__status="published")),
            min_program_price=Min("coach_programs__price_toman", filter=Q(coach_programs__status="published")),
            max_program_price=Max("coach_programs__price_toman", filter=Q(coach_programs__status="published")),
        )
        
        # Apply text search
        if query:
            query_clean = self._normalize_query(query)
            
            search_q = Q()
            for field_name in self.SEARCH_FIELDS:
                search_q |= Q(**{f"{field_name}__icontains": query_clean})
            
            # Also search in specialties (JSON field)
            search_q |= Q(specialties__icontains=query_clean)
            
            queryset = queryset.filter(search_q)
            
            # Update search query stats
            self._update_query_stats(query_clean, "coach")
        
        # Apply filters
        queryset = self._apply_filters(queryset, filters)
        
        # Get total count before pagination
        total_count = queryset.count()
        
        # Apply sorting
        queryset = self._apply_sorting(queryset, sort_by)
        
        # Pagination
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]
        
        # Build results
        results = []
        for coach in queryset:
            result = self._build_coach_result(coach, query)
            results.append(result)
        
        # Log search
        search_log = self._log_search(
            query=query,
            filters=filters,
            result_count=total_count,
            result_ids=[r.id for r in results[:10]],
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address
        )
        
        # Get suggestions if few results
        suggestions = []
        if total_count < 5 and query:
            suggestions = self._get_suggestions(query)
        
        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        return SearchResponse(
            success=True,
            results=results,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            filters_applied=filters,
            available_filters=self._get_available_filters(),
            suggestions=suggestions,
            search_id=search_log.id if search_log else None
        )
    
    def _normalize_query(self, query: str) -> str:
        """Normalize search query"""
        # Remove extra whitespace
        query = " ".join(query.split())
        # Convert Persian numbers to Arabic
        persian_nums = "۰۱۲۳۴۵۶۷۸۹"
        arabic_nums = "0123456789"
        for p, a in zip(persian_nums, arabic_nums):
            query = query.replace(p, a)
        return query.strip()
    
    def _apply_filters(self, queryset, filters: Dict[str, Any]):
        """Apply filters to queryset"""
        
        # Specialty filter (JSON contains)
        if filters.get("specialty"):
            specialties = filters["specialty"]
            if isinstance(specialties, str):
                specialties = [specialties]
            
            specialty_q = Q()
            for spec in specialties:
                specialty_q |= Q(specialties__icontains=spec)
            queryset = queryset.filter(specialty_q)
        
        # City filter
        if filters.get("city"):
            queryset = queryset.filter(city__iexact=filters["city"])
        
        # Rating filter
        if filters.get("min_rating"):
            queryset = queryset.filter(avg_rating__gte=filters["min_rating"])
        
        # Price range filter (based on programs)
        if filters.get("max_price"):
            queryset = queryset.filter(min_program_price__lte=filters["max_price"])
        
        if filters.get("min_price"):
            queryset = queryset.filter(min_program_price__gte=filters["min_price"])
        
        # Experience level filter
        if filters.get("experience_level"):
            levels = filters["experience_level"]
            if isinstance(levels, str):
                levels = [levels]
            
            level_q = Q()
            for level in levels:
                level_q |= Q(target_experience_levels__icontains=level)
            queryset = queryset.filter(level_q)
        
        # Gender filter
        if filters.get("gender"):
            queryset = queryset.filter(gender=filters["gender"])
        
        # Verified filter
        if filters.get("is_verified") is True:
            queryset = queryset.filter(is_verified=True)
        
        # Has availability filter
        if filters.get("has_availability") is True:
            queryset = queryset.filter(has_availability=True)
        
        # Has programs filter (implicit - coaches with at least one program)
        if filters.get("has_programs") is True:
            queryset = queryset.filter(program_count__gt=0)
        
        return queryset
    
    def _apply_sorting(self, queryset, sort_by: str):
        """Apply sorting to queryset"""
        
        sort_options = {
            "relevance": ["-is_verified", "-avg_rating", "-program_count"],
            "rating": ["-avg_rating", "-total_reviews"],
            "price_low": ["min_program_price", "-avg_rating"],
            "price_high": ["-max_program_price", "-avg_rating"],
            "newest": ["-date_joined"],
            "most_programs": ["-program_count", "-avg_rating"],
            "most_clients": ["-total_clients", "-avg_rating"],
        }
        
        order_fields = sort_options.get(sort_by, sort_options["relevance"])
        return queryset.order_by(*order_fields)
    
    def _build_coach_result(self, coach, query: str = "") -> CoachSearchResult:
        """Build CoachSearchResult from coach model"""
        
        # Get highlight snippet if query provided
        highlight = ""
        if query and hasattr(coach, "bio") and coach.bio:
            highlight = self._get_highlight(coach.bio, query)
        
        return CoachSearchResult(
            id=coach.id,
            name=coach.get_full_name() or coach.phone,
            phone=coach.phone,
            bio=getattr(coach, "bio", "") or "",
            city=getattr(coach, "city", "") or "",
            specialties=getattr(coach, "specialties", []) or [],
            avg_rating=Decimal(str(getattr(coach, "avg_rating", 0) or 0)),
            total_reviews=getattr(coach, "total_reviews", 0) or 0,
            total_programs=getattr(coach, "program_count", 0) or 0,
            total_clients=getattr(coach, "total_clients", 0) or 0,
            min_price=getattr(coach, "min_program_price", 0) or 0,
            max_price=getattr(coach, "max_program_price", 0) or 0,
            profile_image=coach.profile_image.url if hasattr(coach, "profile_image") and coach.profile_image else None,
            is_verified=getattr(coach, "is_verified", False),
            years_experience=getattr(coach, "years_experience", 0) or 0,
            highlight=highlight
        )
    
    def _get_highlight(self, text: str, query: str, context_chars: int = 100) -> str:
        """Get highlighted snippet from text"""
        
        if not text or not query:
            return ""
        
        text_lower = text.lower()
        query_lower = query.lower()
        
        pos = text_lower.find(query_lower)
        if pos == -1:
            # Return first part of text
            return text[:context_chars * 2] + "..." if len(text) > context_chars * 2 else text
        
        # Get context around match
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(query) + context_chars)
        
        snippet = text[start:end]
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def _update_query_stats(self, query: str, category: str):
        """Update search query statistics"""
        
        query_normalized = query.lower().strip()
        
        search_query, created = SearchQuery.objects.get_or_create(
            query_normalized=query_normalized,
            defaults={
                "query_text": query,
                "category": category
            }
        )
        
        if not created:
            search_query.search_count = F("search_count") + 1
            search_query.last_searched_at = timezone.now()
            search_query.save(update_fields=["search_count", "last_searched_at"])
    
    def _log_search(
        self,
        query: str,
        filters: Dict,
        result_count: int,
        result_ids: List[uuid.UUID],
        user_id: uuid.UUID = None,
        session_id: str = None,
        ip_address: str = None
    ) -> Optional[SearchLog]:
        """Log search for analytics"""
        
        try:
            return SearchLog.objects.create(
                user_id=user_id,
                search_type=SearchLog.SearchType.COACH,
                query_text=query,
                filters_applied=filters,
                result_count=result_count,
                result_ids=[str(rid) for rid in result_ids],
                session_id=session_id or "",
                ip_address=ip_address
            )
        except Exception:
            return None
    
    def _get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions based on popular queries"""
        
        query_lower = query.lower()
        
        suggestions = SearchQuery.objects.filter(
            query_normalized__icontains=query_lower,
            search_count__gte=3
        ).exclude(
            query_normalized=query_lower
        ).order_by("-search_count")[:5]
        
        return [s.query_text for s in suggestions]
    
    def _get_available_filters(self) -> Dict[str, Any]:
        """Get available filter options with counts"""
        
        # Get cities with coach counts
        cities = User.objects.filter(
            role="coach",
            is_active=True,
            city__isnull=False
        ).exclude(city="").values("city").annotate(
            count=Count("id")
        ).order_by("-count")[:20]
        
        filters = self.AVAILABLE_FILTERS.copy()
        filters["city"]["options"] = [(c["city"], f"{c['city']} ({c['count']})") for c in cities]
        
        return filters
    
    def get_autocomplete(self, query: str, limit: int = 10) -> List[Dict]:
        """Get autocomplete suggestions"""
        
        if len(query) < 2:
            return []
        
        query_lower = query.lower()
        results = []
        
        # Search in popular queries
        queries = SearchQuery.objects.filter(
            query_normalized__istartswith=query_lower
        ).order_by("-search_count")[:limit]
        
        for q in queries:
            results.append({
                "text": q.query_text,
                "type": "query",
                "count": q.search_count
            })
        
        # Search in coach names
        coaches = User.objects.filter(
            role="coach",
            is_active=True
        ).filter(
            Q(first_name__istartswith=query) | Q(last_name__istartswith=query)
        )[:5]
        
        for coach in coaches:
            results.append({
                "text": coach.get_full_name(),
                "type": "coach",
                "id": str(coach.id)
            })
        
        return results[:limit]


class ProgramSearchService:
    """
    Service for searching and filtering programs.
    
    BP: "program purchase delivery (PDF)"
    """
    
    SEARCH_FIELDS = ["title", "short_description", "long_description"]
    
    def search(
        self,
        query: str = "",
        filters: Dict[str, Any] = None,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 20,
        user_id: uuid.UUID = None,
        session_id: str = None,
        ip_address: str = None
    ) -> SearchResponse:
        """
        Search for programs with optional filters.
        """
        
        filters = filters or {}
        page_size = min(page_size, 50)
        
        # Base queryset - published programs only
        queryset = Program.objects.filter(
            status=Program.Status.PUBLISHED
        ).select_related("coach")
        
        # Apply text search
        if query:
            query_clean = query.strip()
            
            search_q = Q()
            for field_name in self.SEARCH_FIELDS:
                search_q |= Q(**{f"{field_name}__icontains": query_clean})
            
            # Also search in tags (JSON field)
            search_q |= Q(tags__icontains=query_clean)
            
            # Search in coach name
            search_q |= Q(coach__first_name__icontains=query_clean)
            search_q |= Q(coach__last_name__icontains=query_clean)
            
            queryset = queryset.filter(search_q)
        
        # Apply filters
        queryset = self._apply_filters(queryset, filters)
        
        # Get total count
        total_count = queryset.count()
        
        # Apply sorting
        queryset = self._apply_sorting(queryset, sort_by)
        
        # Pagination
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]
        
        # Build results
        results = []
        for program in queryset:
            result = self._build_program_result(program)
            results.append(result)
        
        # Log search
        self._log_search(
            query=query,
            filters=filters,
            result_count=total_count,
            result_ids=[r.id for r in results[:10]],
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address
        )
        
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        return SearchResponse(
            success=True,
            results=results,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            filters_applied=filters,
            available_filters=self._get_available_filters()
        )
    
    def _apply_filters(self, queryset, filters: Dict[str, Any]):
        """Apply filters to queryset"""
        
        # Category filter
        if filters.get("category"):
            categories = filters["category"]
            if isinstance(categories, str):
                categories = [categories]
            queryset = queryset.filter(category__in=categories)
        
        # Difficulty filter
        if filters.get("difficulty"):
            difficulties = filters["difficulty"]
            if isinstance(difficulties, str):
                difficulties = [difficulties]
            queryset = queryset.filter(difficulty__in=difficulties)
        
        # Price range
        if filters.get("min_price"):
            queryset = queryset.filter(price_toman__gte=filters["min_price"])
        
        if filters.get("max_price"):
            queryset = queryset.filter(price_toman__lte=filters["max_price"])
        
        # Duration filter
        if filters.get("min_duration"):
            queryset = queryset.filter(duration_weeks__gte=filters["min_duration"])
        
        if filters.get("max_duration"):
            queryset = queryset.filter(duration_weeks__lte=filters["max_duration"])
        
        # Rating filter
        if filters.get("min_rating"):
            queryset = queryset.filter(average_rating__gte=filters["min_rating"])
        
        # Coach filter
        if filters.get("coach_id"):
            queryset = queryset.filter(coach_id=filters["coach_id"])
        
        # Featured filter
        if filters.get("is_featured") is True:
            queryset = queryset.filter(is_featured=True)
        
        # Bestseller filter
        if filters.get("is_bestseller") is True:
            queryset = queryset.filter(is_bestseller=True)
        
        # Has discount filter
        if filters.get("has_discount") is True:
            queryset = queryset.filter(
                original_price_toman__isnull=False,
                original_price_toman__gt=F("price_toman")
            )
        
        return queryset
    
    def _apply_sorting(self, queryset, sort_by: str):
        """Apply sorting to queryset"""
        
        sort_options = {
            "relevance": ["-is_featured", "-is_bestseller", "-total_purchases"],
            "price_low": ["price_toman", "-average_rating"],
            "price_high": ["-price_toman", "-average_rating"],
            "rating": ["-average_rating", "-total_reviews"],
            "newest": ["-published_at"],
            "popular": ["-total_purchases", "-average_rating"],
            "duration_short": ["duration_weeks", "-average_rating"],
            "duration_long": ["-duration_weeks", "-average_rating"],
        }
        
        order_fields = sort_options.get(sort_by, sort_options["relevance"])
        return queryset.order_by(*order_fields)
    
    def _build_program_result(self, program: Program) -> ProgramSearchResult:
        """Build ProgramSearchResult from program model"""
        
        return ProgramSearchResult(
            id=program.id,
            title=program.title,
            short_description=program.short_description,
            coach_id=program.coach_id,
            coach_name=program.coach.get_full_name() if program.coach else "",
            category=program.category,
            difficulty=program.difficulty,
            price=program.price_toman,
            original_price=program.original_price_toman,
            duration_weeks=program.duration_weeks,
            avg_rating=program.average_rating,
            total_reviews=program.total_reviews,
            total_purchases=program.total_purchases,
            thumbnail=program.thumbnail.url if program.thumbnail else None,
            is_featured=program.is_featured,
            is_bestseller=program.is_bestseller,
            discount_percentage=program.discount_percentage
        )
    
    def _log_search(
        self,
        query: str,
        filters: Dict,
        result_count: int,
        result_ids: List[uuid.UUID],
        user_id: uuid.UUID = None,
        session_id: str = None,
        ip_address: str = None
    ):
        """Log search for analytics"""
        
        try:
            SearchLog.objects.create(
                user_id=user_id,
                search_type=SearchLog.SearchType.PROGRAM,
                query_text=query,
                filters_applied=filters,
                result_count=result_count,
                result_ids=[str(rid) for rid in result_ids],
                session_id=session_id or "",
                ip_address=ip_address
            )
        except Exception:
            pass
    
    def _get_available_filters(self) -> Dict[str, Any]:
        """Get available filter options"""
        
        return {
            "category": {
                "type": "multi_select",
                "options": list(Program.Category.choices)
            },
            "difficulty": {
                "type": "multi_select",
                "options": list(Program.Difficulty.choices)
            },
            "price_range": {
                "type": "range",
                "min": 0,
                "max": 10000000
            },
            "duration": {
                "type": "range",
                "min": 1,
                "max": 52
            },
            "min_rating": {
                "type": "range",
                "min": 0,
                "max": 5
            },
            "is_featured": {
                "type": "boolean"
            },
            "is_bestseller": {
                "type": "boolean"
            },
            "has_discount": {
                "type": "boolean"
            }
        }