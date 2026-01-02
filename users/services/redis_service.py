# users/services/redis_service.py
"""
Redis service for MY-FITA
Supports both real Redis and FakeRedis for testing
"""

from typing import Optional, Any, Tuple
from django.conf import settings


class RedisService:
    """
    Centralized Redis client for MY-FITA platform.
    Uses FakeRedis when USE_FAKE_REDIS=True (no Docker needed).
    """

    _instance: Optional["RedisService"] = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize Redis connection."""
        use_fake = getattr(settings, "USE_FAKE_REDIS", True)

        if use_fake:
            # Use FakeRedis for testing (no Docker needed)
            try:
                import fakeredis
                self._client = fakeredis.FakeRedis(decode_responses=True)
            except ImportError:
                # Fallback to in-memory dict
                self._client = InMemoryRedis()
        else:
            # Use real Redis
            import redis
            self._client = redis.Redis(
                host=getattr(settings, "REDIS_HOST", "localhost"),
                port=getattr(settings, "REDIS_PORT", 6379),
                db=getattr(settings, "REDIS_DB", 0),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

    @property
    def client(self):
        """Get Redis client instance."""
        if self._client is None:
            self._initialize()
        return self._client

    def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        try:
            return self._client.get(key)
        except Exception:
            return None

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set value in Redis."""
        try:
            return self._client.set(key, value, ex=ex)
        except Exception:
            return False

    def incr(self, key: str) -> int:
        """Increment counter."""
        try:
            return self._client.incr(key)
        except Exception:
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        try:
            return self._client.expire(key, seconds)
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            return bool(self._client.delete(key))
        except Exception:
            return False

    def ttl(self, key: str) -> int:
        """Get time to live for key."""
        try:
            return self._client.ttl(key)
        except Exception:
            return -1

    def rate_limit_check(
        self,
        identifier: str,
        limit: int = 100,
        window: int = 60
    ) -> Tuple[bool, int]:
        """
        Check if request should be rate limited.

        Returns:
            (is_allowed, remaining_requests)
        """
        key = f"rate_limit:{identifier}"

        try:
            current = self._client.incr(key)

            if current == 1:
                self._client.expire(key, window)

            if current > limit:
                return False, 0

            return True, limit - current

        except Exception:
            # Fail open on errors
            return True, limit


class InMemoryRedis:
    """
    Simple in-memory Redis replacement for testing.
    No external dependencies needed.
    """

    def __init__(self):
        self._data = {}
        self._expiry = {}

    def get(self, key: str) -> Optional[str]:
        self._check_expiry(key)
        return self._data.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._data[key] = str(value)
        if ex:
            import time
            self._expiry[key] = time.time() + ex
        return True

    def incr(self, key: str) -> int:
        self._check_expiry(key)
        current = int(self._data.get(key, 0))
        self._data[key] = str(current + 1)
        return current + 1

    def expire(self, key: str, seconds: int) -> bool:
        import time
        self._expiry[key] = time.time() + seconds
        return True

    def delete(self, key: str) -> int:
        if key in self._data:
            del self._data[key]
            self._expiry.pop(key, None)
            return 1
        return 0

    def ttl(self, key: str) -> int:
        import time
        if key in self._expiry:
            remaining = int(self._expiry[key] - time.time())
            return max(remaining, -1)
        return -1

    def _check_expiry(self, key: str):
        import time
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]


# Singleton instance
redis_service = RedisService()