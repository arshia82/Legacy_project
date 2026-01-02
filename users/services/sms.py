from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException


class SMSService:
    def __init__(self):
        self.api = KavenegarAPI(
            settings.KAVENEGAR_API_KEY,
            timeout=20
        )

    def send_otp(self, phone_number: str, code: str):
        try:
            params = {
                "receptor": phone_number,
                "template": settings.KAVENEGAR_OTP_TEMPLATE,
                "token": code,
                "type": "sms",
            }
            return self.api.verify_lookup(params)

        except APIException as e:
            # API returned error
            raise RuntimeError(f"Kavenegar API error: {e}")

        except HTTPException as e:
            # Network error
            raise RuntimeError(f"Kavenegar HTTP error: {e}")