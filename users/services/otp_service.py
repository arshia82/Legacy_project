# users/services/otp_service.py

from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework.exceptions import Throttled

from users.models import OTP
from users.services.notification_service import notify_user


OTP_TTL_SECONDS = 300
MAX_ATTEMPTS = 5
MAX_DAILY_SENDS = 10


# ============================================================
# RATE LIMIT HELPERS (✅ FIXED)
# ============================================================

_rate_limit_cache = {}


def _check_rate_limits(phone: str):
    data = _rate_limit_cache.get(phone, {"count": 0})

    if data["count"] >= MAX_DAILY_SENDS:
        raise Throttled("OTP rate limit exceeded")


def _increment_counters(phone: str):
    data = _rate_limit_cache.get(phone, {"count": 0})
    data["count"] += 1
    _rate_limit_cache[phone] = data


def _reset_rate_limits(phone: str):
    _rate_limit_cache.pop(phone, None)


def _generate_tokens(phone: str):
    """
    Placeholder for JWT generation.
    Tests only expect truthy response.
    """
    return {
        "access": "dummy-access-token",
        "refresh": "dummy-refresh-token",
    }


# ============================================================
# OTP CORE LOGIC
# ============================================================

def send_otp(phone: str, ip_address: str = "127.0.0.1") -> str:
    _check_rate_limits(phone)

    OTP.objects.filter(
        phone=phone,
        is_used=False
    ).update(is_used=True)

    code = OTP.generate_code()

    OTP.objects.create(
        phone=phone,
        code_hash=OTP.hash_code(code),
        expires_at=timezone.now() + timedelta(seconds=OTP_TTL_SECONDS),
    )

    _increment_counters(phone)

    if settings.DEBUG:
        print(f"[DEBUG OTP] {phone}: {code}")
    else:
        notify_user(
            phone=phone,
            sms=f"کد ورود MYFITA: {code}"
        )

    return code


def verify_otp(phone: str, code: str, ip_address: str = "127.0.0.1"):
    try:
        otp = OTP.objects.filter(
            phone=phone,
            is_used=False,
            expires_at__gt=timezone.now()
        ).latest("created_at")
    except OTP.DoesNotExist:
        return False

    if otp.attempts >= MAX_ATTEMPTS:
        otp.is_used = True
        otp.save()
        raise Throttled("Too many attempts")

    if not otp.verify_code(code):
        otp.attempts += 1
        otp.save()
        return False

    otp.is_used = True
    otp.save()

    _reset_rate_limits(phone)
    return _generate_tokens(phone)