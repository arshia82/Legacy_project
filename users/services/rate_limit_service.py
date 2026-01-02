# users/services/rate_limit_service.py
"""
Rate limiting service using Redis.
Implements sliding window and fixed window algorithms.
"""

import time
from typing import Optional, Tuple
from django.conf import settings

from users.services.redis_service import redis_service


class RateLimitService:
    """
    Production-grade rate limiting with Redis backend.
    """

    # Default limits (can be overridden in settings)
    DEFAULT_LIMITS = {
        'otp_request': {'limit': 5, 'window': 3600},      # 5 per hour
        'otp_verify': {'limit': 10, 'window': 600},       # 10 per 10 min
        'login': {'limit': 10, 'window': 900},            # 10 per 15 min
        'api_global': {'limit': 100, 'window': 60},       # 100 per minute
        'api_user': {'limit': 60, 'window': 60},          # 60 per minute
    }

    def __init__(self):
        self.limits = getattr(
            settings,
            'RATE_LIMITS',
            self.DEFAULT_LIMITS
        )

    def _get_key(
        self,
        action: str,
        identifier: str,
        window: Optional[int] = None
    ) -> str:
        """
        Generate Redis key for rate limit counter.
        """
        if window:
            # Fixed window: key includes timestamp bucket
            bucket = int(time.time()) // window
            return f"ratelimit:{action}:{identifier}:{bucket}"
        else:
            # Sliding window: key without timestamp
            return f"ratelimit:{action}:{identifier}"

    def check_rate_limit(
        self,
        action: str,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Tuple[bool, int, int]:
        """
        Check if action is rate limited.

        Args:
            action: Action type (e.g., 'otp_request')
            identifier: Unique identifier (phone, IP, user_id)
            limit: Max requests (overrides default)
            window: Time window in seconds (overrides default)

        Returns:
            (is_allowed, remaining, reset_time)
        """
        # Get limits
        config = self.limits.get(action, {})
        limit = limit or config.get('limit', 10)
        window = window or config.get('window', 60)

        # Generate key
        key = self._get_key(action, identifier, window)

        # Get current count
        current = redis_service.get(key)

        if current is None:
            # First request in window
            redis_service.set(key, "1", ex=window)
            return True, limit - 1, int(time.time()) + window

        current = int(current)

        if current >= limit:
            # Rate limit exceeded
            ttl = redis_service.client.ttl(key)
            reset_time = int(time.time()) + max(ttl, 0)
            return False, 0, reset_time

        # Increment counter
        redis_service.incr(key)
        ttl = redis_service.client.ttl(key)
        reset_time = int(time.time()) + max(ttl, 0)

        return True, limit - current - 1, reset_time

    def reset_limit(self, action: str, identifier: str) -> bool:
        """
        Reset rate limit for identifier (admin override).
        """
        pattern = f"ratelimit:{action}:{identifier}*"
        keys = list(redis_service.client.scan_iter(match=pattern))

        if keys:
            redis_service.delete(*keys)
            return True
        return False

    def get_remaining(
        self,
        action: str,
        identifier: str
    ) -> Tuple[int, int]:
        """
        Get remaining requests and reset time.
        """
        config = self.limits.get(action, {})
        limit = config.get('limit', 10)
        window = config.get('window', 60)

        key = self._get_key(action, identifier, window)
        current = redis_service.get(key)

        if current is None:
            return limit, int(time.time()) + window

        current = int(current)
        remaining = max(0, limit - current)
        ttl = redis_service.client.ttl(key)
        reset_time = int(time.time()) + max(ttl, 0)

        return remaining, reset_time


# Singleton instance
rate_limit_service = RateLimitService()