# users/decorators/rate_limit.py
"""
Rate limiting decorators for views and API endpoints.
"""

import time  # ← اضافه شد
from functools import wraps
from typing import Optional, Callable

from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status

from users.services.rate_limit_service import rate_limit_service


def rate_limit(
    action: str,
    get_identifier: Optional[Callable] = None,
    limit: Optional[int] = None,
    window: Optional[int] = None
):
    """
    Decorator for rate limiting views.

    Usage:
        @rate_limit('otp_request', get_identifier=lambda req: req.data.get('phone'))
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get identifier
            if get_identifier:
                identifier = get_identifier(request)
            else:
                # Default: use IP address
                identifier = get_client_ip(request)

            if not identifier:
                # If no identifier, allow request (fail open)
                return func(request, *args, **kwargs)

            # Check rate limit
            is_allowed, remaining, reset_time = rate_limit_service.check_rate_limit(
                action=action,
                identifier=identifier,
                limit=limit,
                window=window
            )

            if not is_allowed:
                # Rate limit exceeded
                response_data = {
                    'error': 'rate_limit_exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'retry_after': reset_time
                }

                # Check if DRF or Django view
                if hasattr(request, 'accepted_renderer'):
                    # DRF view
                    return Response(
                        response_data,
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                        headers={'Retry-After': str(reset_time - int(time.time()))}
                    )
                else:
                    # Django view
                    return JsonResponse(
                        response_data,
                        status=429,
                        headers={'Retry-After': str(reset_time - int(time.time()))}
                    )

            # Add rate limit headers
            response = func(request, *args, **kwargs)

            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limit or 10)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(reset_time)

            return response

        return wrapper
    return decorator


def get_client_ip(request) -> str:
    """
    Extract client IP from request.
    Handles X-Forwarded-For properly.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        # Take first IP (client IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')

    return ip