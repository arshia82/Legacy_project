"""
Custom exception handler.
"""
import logging
from rest_framework.views import exception_handler

logger = logging.getLogger("users.security")


def custom_exception_handler(exc, context):
    """Custom exception handler for consistent error format."""
    response = exception_handler(exc, context)
    
    if response is not None:
        error_code = exc.__class__.__name__.upper().replace("EXCEPTION", "")
        
        custom_response = {
            "success": False,
            "error": str(exc.detail) if hasattr(exc, "detail") else str(exc),
            "code": error_code,
        }
        
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            custom_response["details"] = exc.detail
        
        response.data = custom_response
    
    return response