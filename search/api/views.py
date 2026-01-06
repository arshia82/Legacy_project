# FILE: myfita/apps/backend/search/api/views.py

"""
SEARCH API VIEWS

BP: "coach athlete profiles, search filter"
BP: "program purchase delivery (PDF)"

Provides REST API endpoints for:
- Coach search with filters
- Program search with filters
- Autocomplete suggestions
- Saved searches
- Search analytics logging
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.utils import timezone

from search.models import SearchLog, SavedSearch
from search.services.search_service import CoachSearchService, ProgramSearchService
from search.services.filter_service import FilterService
from search.api.serializers import (
    SearchRequestSerializer,
    ProgramSearchRequestSerializer,
    SearchResponseSerializer,
    CoachSearchResultSerializer,
    ProgramSearchResultSerializer,
    SavedSearchSerializer,
    SavedSearchCreateSerializer,
    AutocompleteResultSerializer,
    LogSearchClickSerializer,
)


class SearchRateThrottle(AnonRateThrottle):
    """Rate limiting for search endpoints"""
    rate = '60/minute'


class CoachSearchView(APIView):
    """
    Search for coaches with filters.
    
    BP: "search filter" for coach discovery
    BP: "athlete enters measurements, goals → MY FITA's AI recommends 
         a shortlist of matched coaches"
    """
    
    permission_classes = [AllowAny]
    throttle_classes = [SearchRateThrottle]
    
    @extend_schema(
        summary="Search coaches",
        description="""
        Search for coaches with optional filters and sorting.
        
        **Filters:**
        - `specialty`: Filter by specialization (can be multiple)
        - `city`: Filter by city
        - `min_rating`: Minimum rating (0-5)
        - `max_price`: Maximum program price in Toman
        - `is_verified`: Only verified coaches
        - `has_availability`: Only coaches with capacity
        
        **Sorting:**
        - `relevance`: Best match (default)
        - `rating`: Highest rated
        - `price_low`: Lowest price first
        - `price_high`: Highest price first
        - `newest`: Recently joined
        """,
        parameters=[
            OpenApiParameter(name="q", type=str, description="Search query text"),
            OpenApiParameter(name="page", type=int, description="Page number (default: 1)"),
            OpenApiParameter(name="page_size", type=int, description="Results per page (default: 20, max: 50)"),
            OpenApiParameter(name="sort_by", type=str, description="Sort option"),
            OpenApiParameter(name="specialty", type=str, description="Filter by specialty (repeatable)"),
            OpenApiParameter(name="city", type=str, description="Filter by city"),
            OpenApiParameter(name="min_rating", type=float, description="Minimum rating"),
            OpenApiParameter(name="min_price", type=int, description="Minimum program price"),
            OpenApiParameter(name="max_price", type=int, description="Maximum program price"),
            OpenApiParameter(name="experience_level", type=str, description="Target experience level"),
            OpenApiParameter(name="gender", type=str, description="Coach gender"),
            OpenApiParameter(name="is_verified", type=bool, description="Only verified coaches"),
            OpenApiParameter(name="has_availability", type=bool, description="Only available coaches"),
        ],
        responses={200: SearchResponseSerializer},
        examples=[
            OpenApiExample(
                "Search for weight loss coaches in Tehran",
                value={
                    "q": "کاهش وزن",
                    "city": "تهران",
                    "min_rating": 4.0,
                    "is_verified": True
                }
            )
        ]
    )
    def get(self, request):
        # Parse and validate request parameters
        serializer = SearchRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # Build filters dict from validated data
        filters = {}
        filter_fields = [
            "specialty", "city", "min_rating", "min_price", "max_price",
            "experience_level", "gender", "is_verified", "has_availability"
        ]
        for field in filter_fields:
            value = data.get(field)
            if value is not None and value != "" and value != []:
                filters[field] = value
        
        # Get user info for logging and personalization
        user_id = request.user.id if request.user.is_authenticated else None
        session_id = request.session.session_key or ""
        ip_address = self._get_client_ip(request)
        
        # Perform search
        service = CoachSearchService()
        result = service.search(
            query=data.get("q", ""),
            filters=filters,
            sort_by=data.get("sort_by", "relevance"),
            page=data.get("page", 1),
            page_size=data.get("page_size", 20),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address
        )
        
        # Serialize results
        response_data = {
            "success": result.success,
            "results": [CoachSearchResultSerializer(r).data for r in result.results],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "filters_applied": result.filters_applied,
            "available_filters": result.available_filters,
            "suggestions": result.suggestions,
            "search_id": str(result.search_id) if result.search_id else None,
            "error": result.error,
        }
        
        return Response(response_data)
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class ProgramSearchView(APIView):
    """
    Search for programs with filters.
    
    BP: "program purchase delivery (PDF)"
    """
    
    permission_classes = [AllowAny]
    throttle_classes = [SearchRateThrottle]
    
    @extend_schema(
        summary="Search programs",
        description="""
        Search for training programs with optional filters and sorting.
        
        **Filters:**
        - `category`: Program category (weight_loss, muscle_gain, etc.)
        - `difficulty`: Difficulty level (beginner, intermediate, advanced)
        - `min_price` / `max_price`: Price range in Toman
        - `min_duration` / `max_duration`: Duration in weeks
        - `coach_id`: Filter by specific coach
        - `is_featured`: Featured programs only
        - `is_bestseller`: Bestseller programs only
        - `has_discount`: Programs with discount
        
        **Sorting:**
        - `relevance`: Best match (default)
        - `rating`: Highest rated
        - `price_low` / `price_high`: By price
        - `newest`: Recently published
        - `popular`: Most purchased
        """,
        parameters=[
            OpenApiParameter(name="q", type=str, description="Search query"),
            OpenApiParameter(name="page", type=int, description="Page number"),
            OpenApiParameter(name="page_size", type=int, description="Results per page"),
            OpenApiParameter(name="sort_by", type=str, description="Sort option"),
            OpenApiParameter(name="category", type=str, description="Program category"),
            OpenApiParameter(name="difficulty", type=str, description="Difficulty level"),
            OpenApiParameter(name="min_price", type=int, description="Minimum price"),
            OpenApiParameter(name="max_price", type=int, description="Maximum price"),
            OpenApiParameter(name="min_duration", type=int, description="Minimum duration (weeks)"),
            OpenApiParameter(name="max_duration", type=int, description="Maximum duration (weeks)"),
            OpenApiParameter(name="min_rating", type=float, description="Minimum rating"),
            OpenApiParameter(name="coach_id", type=str, description="Filter by coach UUID"),
            OpenApiParameter(name="is_featured", type=bool, description="Featured only"),
            OpenApiParameter(name="is_bestseller", type=bool, description="Bestsellers only"),
            OpenApiParameter(name="has_discount", type=bool, description="Discounted only"),
        ],
        responses={200: SearchResponseSerializer}
    )
    def get(self, request):
        serializer = ProgramSearchRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # Build filters dict
        filters = {}
        filter_fields = [
            "category", "difficulty", "min_price", "max_price",
            "min_duration", "max_duration", "min_rating",
            "coach_id", "is_featured", "is_bestseller", "has_discount"
        ]
        for field in filter_fields:
            value = data.get(field)
            if value is not None and value != "" and value != []:
                filters[field] = value
        
        # Get user info
        user_id = request.user.id if request.user.is_authenticated else None
        session_id = request.session.session_key or ""
        ip_address = self._get_client_ip(request)
        
        # Perform search
        service = ProgramSearchService()
        result = service.search(
            query=data.get("q", ""),
            filters=filters,
            sort_by=data.get("sort_by", "relevance"),
            page=data.get("page", 1),
            page_size=data.get("page_size", 20),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address
        )
        
        response_data = {
            "success": result.success,
            "results": [ProgramSearchResultSerializer(r).data for r in result.results],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "filters_applied": result.filters_applied,
            "available_filters": result.available_filters,
            "suggestions": result.suggestions,
            "search_id": str(result.search_id) if result.search_id else None,
            "error": result.error,
        }
        
        return Response(response_data)
    
    def _get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class AutocompleteView(APIView):
    """
    Get autocomplete suggestions for search.
    
    Provides real-time suggestions as user types.
    """
    
    permission_classes = [AllowAny]
    throttle_classes = [SearchRateThrottle]
    
    @extend_schema(
        summary="Get autocomplete suggestions",
        description="Returns search suggestions based on partial query input.",
        parameters=[
            OpenApiParameter(name="q", type=str, description="Partial search query (min 2 chars)"),
            OpenApiParameter(name="type", type=str, description="Search type: coach or program"),
            OpenApiParameter(name="limit", type=int, description="Max suggestions (default: 10)"),
        ],
        responses={200: AutocompleteResultSerializer(many=True)}
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        search_type = request.query_params.get("type", "coach")
        limit = min(int(request.query_params.get("limit", 10)), 20)
        
        # Minimum query length
        if len(query) < 2:
            return Response([])
        
        # Get suggestions based on type
        if search_type == "program":
            service = ProgramSearchService()
        else:
            service = CoachSearchService()
        
        try:
            results = service.get_autocomplete(query, limit)
            return Response(results)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FilterOptionsView(APIView):
    """
    Get available filter options with counts.
    
    Returns all available filter options for the search UI.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get filter options",
        description="Returns available filter options with labels and counts.",
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                description="Filter type: coach or program",
                default="coach"
            ),
        ]
    )
    def get(self, request):
        filter_type = request.query_params.get("type", "coach")
        
        service = FilterService()
        definitions = service.get_filter_definitions(filter_type)
        
        # Convert to dict format for frontend
        result = {}
        for defn in definitions:
            filter_data = {
                "label": defn.label,
                "type": defn.type,
            }
            
            if defn.options:
                filter_data["options"] = [
                    {"value": opt.value, "label": opt.label, "count": opt.count}
                    for opt in defn.options
                ]
            
            if defn.min_value is not None:
                filter_data["min"] = defn.min_value
            if defn.max_value is not None:
                filter_data["max"] = defn.max_value
            if defn.step is not None:
                filter_data["step"] = defn.step
            
            result[defn.name] = filter_data
        
        # Add price suggestions
        result["price_suggestions"] = service.get_price_suggestions(filter_type)
        
        return Response(result)


class SavedSearchListView(APIView):
    """
    List and create saved searches.
    
    Allows users to save search configurations for quick access.
    """
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List saved searches",
        responses={200: SavedSearchSerializer(many=True)}
    )
    def get(self, request):
        searches = SavedSearch.objects.filter(
            user=request.user
        ).order_by("-created_at")[:50]
        
        serializer = SavedSearchSerializer(searches, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Create saved search",
        request=SavedSearchCreateSerializer,
        responses={201: SavedSearchSerializer}
    )
    def post(self, request):
        # Limit saved searches per user
        existing_count = SavedSearch.objects.filter(user=request.user).count()
        if existing_count >= 20:
            return Response(
                {"detail": "حداکثر ۲۰ جستجوی ذخیره شده مجاز است."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SavedSearchCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        
        if serializer.is_valid():
            instance = serializer.save()
            return Response(
                SavedSearchSerializer(instance).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SavedSearchDetailView(APIView):
    """
    Retrieve, update, or delete a saved search.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        try:
            return SavedSearch.objects.get(pk=pk, user=user)
        except SavedSearch.DoesNotExist:
            return None
    
    @extend_schema(
        summary="Get saved search",
        responses={200: SavedSearchSerializer}
    )
    def get(self, request, pk):
        search = self.get_object(pk, request.user)
        if not search:
            return Response(
                {"detail": "جستجوی ذخیره شده یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SavedSearchSerializer(search)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Update saved search",
        request=SavedSearchCreateSerializer,
        responses={200: SavedSearchSerializer}
    )
    def patch(self, request, pk):
        search = self.get_object(pk, request.user)
        if not search:
            return Response(
                {"detail": "جستجوی ذخیره شده یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SavedSearchCreateSerializer(
            search,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        
        if serializer.is_valid():
            instance = serializer.save()
            return Response(SavedSearchSerializer(instance).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary="Delete saved search")
    def delete(self, request, pk):
        search = self.get_object(pk, request.user)
        if not search:
            return Response(
                {"detail": "جستجوی ذخیره شده یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        search.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogSearchClickView(APIView):
    """
    Log when user clicks a search result.
    
    Used for analytics and improving search relevance.
    BP: "captures structured data... enabling better personalization"
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Log search result click",
        request=LogSearchClickSerializer,
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}}}}
    )
    def post(self, request):
        serializer = LogSearchClickSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Update search log with click data
            SearchLog.objects.filter(
                id=data["search_id"]
            ).update(
                clicked_result_id=data["result_id"],
                clicked_at=timezone.now()
            )
            
            return Response({"success": True})
        
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PopularSearchesView(APIView):
    """
    Get popular/trending searches.
    
    Returns most searched queries for discovery.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get popular searches",
        parameters=[
            OpenApiParameter(name="limit", type=int, description="Max results (default: 10)"),
            OpenApiParameter(name="category", type=str, description="Filter by category"),
        ]
    )
    def get(self, request):
        from search.models import SearchQuery
        
        limit = min(int(request.query_params.get("limit", 10)), 20)
        category = request.query_params.get("category", "")
        
        queryset = SearchQuery.objects.filter(
            search_count__gte=5  # Minimum searches to be "popular"
        ).order_by("-search_count")
        
        if category:
            queryset = queryset.filter(category=category)
        
        queries = queryset[:limit]
        
        return Response([
            {
                "query": q.query_text,
                "count": q.search_count,
                "category": q.category
            }
            for q in queries
        ])