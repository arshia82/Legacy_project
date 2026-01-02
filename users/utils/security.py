"""
Security utilities for OTP system.
"""
import hmac
import hashlib
import secrets
import time
from typing import Tuple
from django.conf import settings


class OTPSecurity:
    """Cryptographic utilities for OTP."""
    
    def __init__(self):
        config = getattr(settings, "OTP_CONFIG", {})
        self.hmac_secret = config.get("HMAC_SECRET", "default-secret").encode()
        self.code_length = config.get("CODE_LENGTH", 6)
    
    def generate_otp(self) -> str:
        """Generate cryptographically secure OTP."""
        otp_int = secrets.randbelow(10 ** self.code_length)
        return str(otp_int).zfill(self.code_length)
    
    def generate_salt(self) -> str:
        """Generate random salt."""
        return secrets.token_hex(16)
    
    def hash_otp(self, otp: str, salt: str) -> str:
        """Create HMAC-SHA256 hash of OTP."""
        message = f"{salt}:{otp}".encode()
        return hmac.new(self.hmac_secret, message, hashlib.sha256).hexdigest()
    
    def verify_otp(self, otp: str, salt: str, stored_hash: str) -> bool:
        """Verify OTP using constant-time comparison."""
        computed_hash = self.hash_otp(otp, salt)
        return hmac.compare_digest(computed_hash, stored_hash)
    
    def generate_otp_with_hash(self) -> Tuple[str, str, str]:
        """Generate OTP, salt, and hash."""
        otp = self.generate_otp()
        salt = self.generate_salt()
        otp_hash = self.hash_otp(otp, salt)
        return otp, salt, otp_hash


class RateLimitTracker:
    """In-memory rate limit tracking."""
    
    def __init__(self):
        self._requests: dict = {}
    
    def record_request(self, key: str, action: str):
        """Record a request."""
        full_key = f"{key}:{action}"
        if full_key not in self._requests:
            self._requests[full_key] = []
        self._requests[full_key].append(time.time())
        
        # Cleanup old entries
        cutoff = time.time() - 3600
        self._requests[full_key] = [t for t in self._requests[full_key] if t > cutoff]
    
    def get_request_count(self, key: str, action: str, window_seconds: int) -> int:
        """Get count of requests in time window."""
        full_key = f"{key}:{action}"
        if full_key not in self._requests:
            return 0
        cutoff = time.time() - window_seconds
        return sum(1 for t in self._requests[full_key] if t > cutoff)
    
    def get_last_request_time(self, key: str, action: str) -> float:
        """Get timestamp of last request."""
        full_key = f"{key}:{action}"
        if full_key not in self._requests or not self._requests[full_key]:
            return 0
        return max(self._requests[full_key])


# Global instances
otp_security = OTPSecurity()
rate_limiter = RateLimitTracker()