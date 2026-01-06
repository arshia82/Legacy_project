# FILE: myfita/apps/backend/core/health_urls.py

from django.urls import path
from django.http import JsonResponse


def health_check(request):
    """Basic health check endpoint"""
    return JsonResponse({"status": "healthy"})


def readiness_check(request):
    """Readiness probe for Kubernetes/Docker"""
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ready"})
    except Exception as e:
        return JsonResponse({"status": "not ready", "error": str(e)}, status=503)


def liveness_check(request):
    """Liveness probe"""
    return JsonResponse({"status": "alive"})


urlpatterns = [
    path("", health_check, name="health"),
    path("ready/", readiness_check, name="readiness"),
    path("live/", liveness_check, name="liveness"),
]