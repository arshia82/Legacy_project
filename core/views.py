# FILE: myfita/apps/backend/core/views.py

"""
CORE VIEWS

System-level views including health checks and error handlers.
"""

import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Comprehensive health check endpoint.
    
    Checks:
    - Database connectivity
    - Cache connectivity
    - Disk space (if applicable)
    """
    
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request):
        health_status = {
            "status": "healthy",
            "checks": {}
        }
        
        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["checks"]["database"] = "ok"
        except Exception as e:
            health_status["checks"]["database"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"
        
        # Cache check
        try:
            cache.set("health_check", "ok", 10)
            if cache.get("health_check") == "ok":
                health_status["checks"]["cache"] = "ok"
            else:
                health_status["checks"]["cache"] = "error: cache read failed"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["cache"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return Response(health_status, status=status_code)


class ReadinessCheckView(APIView):
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the service is ready to accept traffic.
    """
    
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request):
        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return Response({"status": "ready"})
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return Response(
                {"status": "not ready", "error": str(e)},
                status=503
            )


class LivenessCheckView(APIView):
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the service is alive.
    """
    
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request):
        return Response({"status": "alive"})


def custom_404(request, exception=None):
    """Custom 404 error handler"""
    return JsonResponse(
        {
            "error": "not_found",
            "message": "صفحه مورد نظر یافت نشد.",
            "status_code": 404
        },
        status=404
    )


def custom_500(request):
    """Custom 500 error handler"""
    return JsonResponse(
        {
            "error": "server_error",
            "message": "خطای سرور. لطفاً بعداً تلاش کنید.",
            "status_code": 500
        },
        status=500
    )