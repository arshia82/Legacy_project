# users/otp_config.py
"""
OTP Security Configuration
Aligned with MY_FITA Business Plan:
- Operations (p.9): Phone OTP verification
- Risk (p.14): Fraud/disintermediation mitigation
"""

from datetime import timedelta

# ============================================================
# OTP CODE SETTINGS (15 points)
# ============================================================
OTP_CODE_LENGTH = 6  # 6-digit numeric code
OTP_TTL_SECONDS = 300  # 5 minutes expiry
OTP_ALGORITHM = 'sha256'  # For hashing stored codes

# ============================================================
# ATTEMPT TRACKING & LOCKOUT (25 points)
# ============================================================
# Per-phone limits
MAX_VERIFY_ATTEMPTS_PER_PHONE = 5  # Max wrong codes before lock
VERIFY_ATTEMPT_WINDOW_SECONDS = 600  # 10-minute sliding window

# Progressive lockout durations
LOCKOUT_DURATIONS = {
    1: timedelta(minutes=1),   # After 5 fails: 1 min
    2: timedelta(minutes=5),   # After 10 fails: 5 min
    3: timedelta(minutes=15),  # After 15 fails: 15 min
    4: timedelta(hours=1),     # After 20 fails: 1 hour
    5: timedelta(hours=24),    # After 25+ fails: 24 hours (manual review)
}

# Per-IP limits
MAX_REQUESTS_PER_IP_HOUR = 30  # OTP requests per IP per hour
MAX_VERIFY_PER_IP_HOUR = 50    # Verify attempts per IP per hour

# ============================================================
# RATE LIMITING - SMS SENDS (15 points)
# ============================================================
MAX_OTP_SENDS_PER_PHONE_30MIN = 3   # Max 3 OTPs in 30 minutes
MAX_OTP_SENDS_PER_PHONE_DAY = 10    # Max 10 OTPs per day
COOLDOWN_BETWEEN_SENDS_SECONDS = 60  # 1 minute between sends

# ============================================================
# ANTI-ENUMERATION (10 points)
# ============================================================
# Always return same response regardless of phone validity
GENERIC_SEND_RESPONSE = "If this phone number is valid, you will receive an OTP shortly."
GENERIC_VERIFY_RESPONSE = "Invalid OTP or verification failed."
GENERIC_LOCKOUT_RESPONSE = "Too many attempts. Please try again later."

# Response timing padding (prevent timing attacks)
MIN_RESPONSE_TIME_MS = 200
MAX_RESPONSE_TIME_MS = 500

# ============================================================
# DELIVERY SAFETY (5 points)
# ============================================================
SMS_PROVIDER = 'kavenegar'
SMS_SENDER_NUMBER = '2000660110'  # From your Kavenegar account

# ============================================================
# MONITORING & ALERTING (15 points)
# ============================================================
ALERT_THRESHOLDS = {
    'failed_verifications_per_minute': 50,
    'unique_ips_per_phone_10min': 5,
    'sms_sends_per_minute': 20,
    'lockouts_per_hour': 10,
}

# ============================================================
# SECURITY FLAGS
# ============================================================
REQUIRE_CAPTCHA_AFTER_FAILS = 3  # Show CAPTCHA after 3 fails
ENABLE_DEVICE_FINGERPRINTING = True
ENABLE_IP_REPUTATION_CHECK = False  # Enable when you have IP database