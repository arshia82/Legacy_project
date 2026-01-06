# FILE: myfita/apps/backend/matching/api/views.py

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from matching.models import AthletePreferences, MatchResult
from matching.services.matching_service import CoachMatchingService
from matching.api.serializers import (
    AthletePreferencesSerializer,
    AthletePreferencesCreateSerializer,
    MatchingResultSerializer,
    MatchResultSerializer,
    LogInteractionSerializer,
)


class AthletePreferencesView(APIView):
    """
    GET: Retrieve athlete's matching preferences
    POST: Create/update preferences (quiz submission)
    """
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get athlete preferences",
        responses={200: AthletePreferencesSerializer}
    )
    def get(self, request):
        try:
            preferences = AthletePreferences.objects.get(athlete=request.user)
            serializer = AthletePreferencesSerializer(preferences)
            return Response(serializer.data)
        except AthletePreferences.DoesNotExist:
            return Response(
                {"detail": "پرسشنامه تطبیق هنوز تکمیل نشده است."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Submit matching quiz",
        request=AthletePreferencesCreateSerializer,
        responses={201: AthletePreferencesSerializer}
    )
    def post(self, request):
        serializer = AthletePreferencesCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        
        if serializer.is_valid():
            instance = serializer.save()
            return Response(
                AthletePreferencesSerializer(instance).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CoachMatchingView(APIView):
    """
    GET: Get matched coaches for authenticated athlete
    
    BP: "athlete enters measurements, goals and training history → 
         MY FITA's AI recommends a shortlist of matched coaches"
    """
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get matched coaches",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                description="Maximum number of matches to return (default: 10)"
            ),
            OpenApiParameter(
                name="refresh",
                type=bool,
                description="Force refresh cached results"
            ),
        ],
        responses={200: MatchingResultSerializer}
    )
    def get(self, request):
        # Validate user is athlete
        if request.user.role != "athlete":
            return Response(
                {"detail": "فقط ورزشکاران می‌توانند از تطبیق استفاده کنند."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        limit = int(request.query_params.get("limit", 10))
        force_refresh = request.query_params.get("refresh", "").lower() == "true"
        
        # Limit max results
        limit = min(limit, 50)
        
        service = CoachMatchingService()
        result = service.match_coaches(
            athlete_id=request.user.id,
            limit=limit,
            force_refresh=force_refresh
        )
        
        serializer = MatchingResultSerializer(result)
        return Response(serializer.data)


class MatchHistoryView(APIView):
    """
    GET: Get athlete's match history
    """
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get match history",
        responses={200: MatchResultSerializer(many=True)}
    )
    def get(self, request):
        matches = MatchResult.objects.filter(
            athlete=request.user,
            is_stale=False
        ).select_related("coach").order_by("-score")[:50]
        
        serializer = MatchResultSerializer(matches, many=True)
        return Response(serializer.data)


class LogInteractionView(APIView):
    """
    POST: Log user interaction for ML training data
    
    BP: "captures structured data... enabling better personalization"
    """
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Log matching interaction",
        request=LogInteractionSerializer,
        responses={201: {"type": "object", "properties": {"success": {"type": "boolean"}}}}
    )
    def post(self, request):
        serializer = LogInteractionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        service = CoachMatchingService()
        
        try:
            service.log_interaction(
                athlete_id=request.user.id,
                coach_id=serializer.validated_data["coach_id"],
                action=serializer.validated_data["action"],
                context=serializer.validated_data.get("context", {}),
                session_id=serializer.validated_data.get("session_id")
            )
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )