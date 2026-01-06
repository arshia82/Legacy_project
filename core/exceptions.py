# FILE: myfita/apps/backend/core/exceptions.py

"""
CUSTOM EXCEPTIONS

Application-specific exceptions with proper error handling.
"""

from rest_framework.exceptions import APIException
from rest_framework import status


class BusinessLogicException(APIException):
    """Base exception for business logic errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "خطای منطق کسب‌وکار رخ داد."
    default_code = "business_error"


class PaymentException(BusinessLogicException):
    """Payment-related errors"""
    default_detail = "خطا در پردازش پرداخت."
    default_code = "payment_error"


class InsufficientBalanceException(PaymentException):
    """Insufficient balance for transaction"""
    default_detail = "موجودی کافی نیست."
    default_code = "insufficient_balance"


class ProgramDeliveryException(BusinessLogicException):
    """Program delivery errors"""
    default_detail = "خطا در تحویل برنامه."
    default_code = "delivery_error"


class VerificationException(BusinessLogicException):
    """Verification-related errors"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "خطا در تایید هویت."
    default_code = "verification_error"


class CoachNotVerifiedException(VerificationException):
    """Coach is not verified"""
    default_detail = "مربی هنوز تایید نشده است."
    default_code = "coach_not_verified"


class RateLimitException(APIException):
    """Rate limit exceeded"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "تعداد درخواست‌ها بیش از حد مجاز است. لطفاً کمی صبر کنید."
    default_code = "rate_limit_exceeded"


class DisintermediationException(BusinessLogicException):
    """
    Disintermediation attempt detected.
    
    BP Risk: "Disintermediation Fraud - Coaches Will Bypass the Platform"
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "این عملیات مجاز نیست."
    default_code = "disintermediation_detected"


class TokenException(BusinessLogicException):
    """Trust token errors"""
    default_detail = "خطا در توکن امنیتی."
    default_code = "token_error"


class TokenExpiredException(TokenException):
    """Token has expired"""
    default_detail = "توکن منقضی شده است."
    default_code = "token_expired"


class TokenAlreadyUsedException(TokenException):
    """Token has already been used"""
    default_detail = "این توکن قبلاً استفاده شده است."
    default_code = "token_used"


class TokenIntegrityException(TokenException):
    """Token integrity check failed"""
    default_detail = "یکپارچگی توکن تایید نشد."
    default_code = "token_integrity_failed"


class CommissionException(BusinessLogicException):
    """Commission calculation errors"""
    default_detail = "خطا در محاسبه کمیسیون."
    default_code = "commission_error"


class MatchingException(BusinessLogicException):
    """Matching service errors"""
    default_detail = "خطا در سرویس تطبیق."
    default_code = "matching_error"


class ProfileIncompleteException(MatchingException):
    """Profile is incomplete for matching"""
    default_detail = "لطفاً ابتدا پروفایل خود را تکمیل کنید."
    default_code = "profile_incomplete"


class SearchException(BusinessLogicException):
    """Search service errors"""
    default_detail = "خطا در جستجو."
    default_code = "search_error"


# Exception handler for DRF
def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.
    """
    from rest_framework.views import exception_handler
    
    response = exception_handler(exc, context)
    
    if response is not None:
        # Add error code to response
        response.data["error_code"] = getattr(exc, "default_code", "error")
        
        # Ensure consistent structure
        if "detail" in response.data:
            response.data["message"] = response.data.pop("detail")
        
        response.data["success"] = False
    
    return response