import time
import hmac
import hashlib
import secrets
from django.conf import settings

def generate_trust_token(user_id: int, action: str, ttl: int = 3600):
    nonce = secrets.token_urlsafe(16)
    expires_at = int(time.time()) + ttl

    payload = f"{user_id}:{action}:{nonce}:{expires_at}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return payload, signature


def validate_trust_token(payload: str, signature: str) -> bool:
    try:
        user_id, action, nonce, expires_at = payload.split(":")
        expires_at = int(expires_at)
    except ValueError:
        return False

    if int(time.time()) > expires_at:
        return False

    expected = hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)