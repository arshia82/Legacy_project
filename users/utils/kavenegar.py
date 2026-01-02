"""
Kavenegar SMS integration.
"""
import logging
from typing import Tuple
from django.conf import settings

logger = logging.getLogger("users.security")

try:
    from kavenegar import KavenegarAPI, APIException, HTTPException
    KAVENEGAR_AVAILABLE = True
except ImportError:
    KAVENEGAR_AVAILABLE = False
    logger.warning("Kavenegar library not installed")


class KavenegarService:
    """Service for sending SMS via Kavenegar."""
    
    def __init__(self):
        config = getattr(settings, "KAVENEGAR", {})
        self.api_key = config.get("API_KEY", "")
        self.sender = config.get("SENDER", "2000660110")
        self._api = None
    
    @property
    def api(self):
        """Lazy initialization of API client."""
        if self._api is None and KAVENEGAR_AVAILABLE and self.api_key:
            self._api = KavenegarAPI(self.api_key)
        return self._api
    
    def send_otp(self, phone: str, otp: str) -> Tuple[bool, str]:
        """Send OTP via SMS."""
        
        if not KAVENEGAR_AVAILABLE:
            logger.error("Kavenegar library not installed")
            return False, "SMS service unavailable"
        
        if not self.api:
            logger.error("Kavenegar API not configured")
            return False, "SMS service not configured"
        
        message = f"کد تایید MY FITA: {otp}\nاین کد تا ۵ دقیقه معتبر است."
        
        try:
            logger.info(f"Sending OTP to {phone[:4]}***")
            
            response = self.api.sms_send({
                "receptor": phone,
                "sender": self.sender,
                "message": message,
            })
            
            if response and len(response) > 0:
                status_code = response[0].get("status")
                if status_code in [1, 2, 4, 5, 10]:
                    logger.info(f"OTP sent successfully to {phone[:4]}***")
                    return True, "OTP sent successfully"
            
            return False, "SMS delivery failed"
            
        except APIException as e:
            logger.error(f"Kavenegar API error: {e}")
            return False, "SMS service error"
        except HTTPException as e:
            logger.error(f"Kavenegar HTTP error: {e}")
            return False, "SMS service connection error"
        except Exception as e:
            logger.error(f"Unexpected SMS error: {e}")
            return False, "SMS service error"


# Global instance
kavenegar_service = KavenegarService()