"""
Redis-based rate limiting middleware for MY-FITA
Protects against brute force and DoS attacks
"""

import redis  # ✅ FIX
from typing import Callable
from django.http import HttpRequest, JsonResponse
from django.conf import settings

from users.services.redis_service import redis_service


class RateLimitMiddleware:
    """
    Global rate limiting middleware.
    Uses Redis for distributed rate limiting across multiple servers.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Skip rate limiting for certain paths
        if self._should_skip(request):
            return self.get_response(request)
        
        # Get identifier
        identifier = self._get_identifier(request)
        
        # Check rate limit
        is_allowed, remaining = redis_service.rate_limit_check(
            identifier=identifier,
            limit=self._get_limit(request),
            window=60  # 1 minute window
        )
        
        if not is_allowed:
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                status=429
            )
        
        # Add rate limit headers
        response = self.get_response(request)
        response['X-RateLimit-Limit'] = str(self._get_limit(request))
        response['X-RateLimit-Remaining'] = str(remaining)
        
        return response

    def _get_identifier(self, request: HttpRequest) -> str:
        """Get unique identifier for rate limiting."""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        return f"ip:{self._get_client_ip(request)}"

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    def _get_limit(self, request: HttpRequest) -> int:
        """Get rate limit based on endpoint."""
        path = request.path
        
        # Strict limits for sensitive endpoints
        if '/api/auth/' in path or '/api/otp/' in path:
            return 10  # 10 requests per minute
        
        # Medium limits for API endpoints
        if '/api/' in path:
            return 100  # 100 requests per minute
        
        # Lenient for static/public
        return 200

    def _should_skip(self, request: HttpRequest) -> bool:
        """Check if rate limiting should be skipped."""
        # Skip for health checks
        if request.path in ['/health/', '/api/health/']:
            return True
        
        # Skip for admin (optional)
        if request.user.is_authenticated and request.user.is_staff:
            return True
        
        return False