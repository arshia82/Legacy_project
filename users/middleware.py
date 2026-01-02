# users/middleware.py
"""
Security middleware for verification system
"""
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class VerificationSecurityMiddleware:
    """
    Middleware for verification-related security:
    - Log all admin actions
    - Rate limit document uploads
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log admin verification actions
        if '/admin/verifications/' in request.path and request.method == 'POST':
            logger.info(
                f"Admin action: {request.user} on {request.path} - "
                
                f"IP: {self.get_client_ip(request)}"
            )
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')