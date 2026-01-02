import hmac
import hashlib
import time
from django.conf import settings

SECRET = settings.SECRET_KEY.encode()

def sign_media_access(media_id, user_id, ttl=60):
    expires = int(time.time()) + ttl
    payload = f"{media_id}:{user_id}:{expires}"
    signature = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return {
        "token": signature,
        "expires": expires
    }

def verify_signature(media_id, user_id, token, expires):
    if time.time() > expires:
        return False
    payload = f"{media_id}:{user_id}:{expires}"
    expected = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)