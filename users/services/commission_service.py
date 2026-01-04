from decimal import Decimal, ROUND_HALF_UP
import time
import secrets
import hashlib

MIN_COMMISSION = Decimal("1")  # 1 toman floor


def calculate_commission(amount, user):
    """
    Calculates commission based on per-user rate.
    """
    amount = Decimal(amount)

    if amount <= 0:
        return Decimal("0")

    rate = user.commission_rate or Decimal("0.12")

    fee = (amount * rate).quantize(
        Decimal("1."), rounding=ROUND_HALF_UP
    )

    return max(fee, MIN_COMMISSION)


def generate_trust_token(user_id: int, action: str, ttl: int = 3600):
    """
    Generates a short-lived trust token for sensitive actions
    (verification submit, approval, payout, delivery).
    """
    expires_at = int(time.time()) + ttl
    nonce = secrets.token_hex(8)

    raw = f"{user_id}:{action}:{expires_at}:{nonce}"
    signature = hashlib.sha256(raw.encode()).hexdigest()

    return raw, signature


def validate_trust_token(raw: str, signature: str):
    """
    Validates a previously generated trust token.
    Returns (is_valid: bool, payload: dict | None)
    """
    try:
        user_id, action, expires_at, nonce = raw.split(":")
        expires_at = int(expires_at)

        if int(time.time()) > expires_at:
            return False, None

        expected_signature = hashlib.sha256(raw.encode()).hexdigest()

        if not secrets.compare_digest(expected_signature, signature):
            return False, None

        return True, {
            "user_id": int(user_id),
            "action": action,
            "expires_at": expires_at,
        }

    except Exception:
        return False, None