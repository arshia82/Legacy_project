# FILE: myfita/apps/backend/core/middleware.py

"""
CUSTOM MIDDLEWARE

Request/response processing middleware for:
- Request logging
- Performance monitoring
- Security headers
- Error handling
"""

import time
import uuid
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Log all incoming requests with timing information.
    
    Adds request ID for tracing across services.
    """
    
    def process_request(self, request):
        # Generate unique request ID
        request.request_id = str(uuid.uuid4())[:8]
        request.start_time = time.time()
        
        # Log request
        logger.info(
            f"[{request.request_id}] {request.method} {request.path} "
            f"- User: {getattr(request.user, 'id', 'anonymous')}"
        )
    
    def process_response(self, request, response):
        # Calculate duration
        if hasattr(request, "start_time"):
            duration_ms = (time.time() - request.start_time) * 1000
            
            # Add timing header
            response["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"
            
            # Log response
            logger.info(
                f"[{getattr(request, 'request_id', 'unknown')}] "
                f"Response: {response.status_code} ({duration_ms:.2f}ms)"
            )
            
            # Warn on slow requests
            if duration_ms > 1000:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration_ms:.2f}ms"
                )
        
        # Add request ID to response
        if hasattr(request, "request_id"):
            response["X-Request-ID"] = request.request_id
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.
    """
    
    def process_response(self, request, response):
        # Prevent clickjacking
        response["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS filter
        response["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )
        
        return response


class ExceptionHandlerMiddleware(MiddlewareMixin):
    """
    Global exception handler for unhandled errors.
    
    Ensures consistent error response format.
    """
    
    def process_exception(self, request, exception):
        # Log the exception
        logger.exception(
            f"Unhandled exception in {request.method} {request.path}: {exception}"
        )
        
        # Return JSON error response
        return JsonResponse(
            {
                "error": "server_error",
                "message": "خطای غیرمنتظره رخ داد. لطفاً بعداً تلاش کنید.",
                "request_id": getattr(request, "request_id", None)
            },
            status=500
        )


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Maintenance mode middleware.
    
    When enabled, returns 503 for all requests except health checks.
    """
    
    ALLOWED_PATHS = ["/health/", "/health/live/", "/health/ready/"]
    
    def process_request(self, request):
        from django.conf import settings
        
        # Check if maintenance mode is enabled
        if getattr(settings, "MAINTENANCE_MODE", False):
            if request.path not in self.ALLOWED_PATHS:
                return JsonResponse(
                    {
                        "error": "maintenance",
                        "message": "سیستم در حال بروزرسانی است. لطفاً بعداً مراجعه کنید.",
                    },
                    status=503
                )
        
        return None