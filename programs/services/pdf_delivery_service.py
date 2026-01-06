# FILE: myfita/apps/backend/programs/services/pdf_delivery_service.py

"""
SECURE PDF DELIVERY SERVICE

Security Features:
1. Time-limited download tokens (default 30 minutes)
2. Single-use or limited-use tokens
3. IP binding (optional)
4. Purchase verification before download
5. Download count limiting
6. File integrity verification (SHA-256)
7. Audit logging of all downloads
8. Signed URLs for CDN delivery (future)

BP: "program purchase delivery (PDF)"
"""

import hashlib
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.http import FileResponse, HttpResponse
from django.core.files.storage import default_storage

from programs.models import Purchase, DownloadToken, Program
from billing.models import AuditLog

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a download attempt"""
    success: bool
    file_response: Optional[FileResponse] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class PDFDeliveryService:
    """
    Secure PDF delivery service with multiple security layers.
    
    Usage:
        service = PDFDeliveryService()
        
        # Generate download link
        result = service.generate_download_token(purchase_id, request)
        if result['success']:
            download_url = result['download_url']
        
        # Process download
        result = service.process_download(token, request)
        if result.success:
            return result.file_response
    """
    
    # Configuration
    DEFAULT_TOKEN_EXPIRY_MINUTES = 30
    DEFAULT_MAX_USES = 1
    MAX_DOWNLOADS_PER_PURCHASE = 5
    ENABLE_IP_BINDING = False  # Set True for stricter security

    def generate_download_token(
        self,
        purchase_id: str,
        request,
        expires_in_minutes: int = None,
        max_uses: int = None
    ) -> dict:
        """
        Generate a secure download token for a purchase.
        
        Args:
            purchase_id: UUID of the purchase
            request: HTTP request object
            expires_in_minutes: Token validity period
            max_uses: Maximum download attempts
            
        Returns:
            Dict with success status, download_url or error
        """
        
        expires_in = expires_in_minutes or self.DEFAULT_TOKEN_EXPIRY_MINUTES
        max_uses = max_uses or self.DEFAULT_MAX_USES
        
        try:
            purchase = Purchase.objects.select_related('program', 'athlete').get(
                id=purchase_id
            )
        except Purchase.DoesNotExist:
            return {
                'success': False,
                'error': 'Purchase not found',
                'error_code': 'PURCHASE_NOT_FOUND'
            }
        
        # Verify purchase status
        if purchase.status not in [Purchase.Status.PAID, Purchase.Status.DELIVERED]:
            return {
                'success': False,
                'error': 'Purchase not paid',
                'error_code': 'PURCHASE_NOT_PAID'
            }
        
        # Check download limit
        if purchase.download_count >= self.MAX_DOWNLOADS_PER_PURCHASE:
            return {
                'success': False,
                'error': 'Download limit exceeded',
                'error_code': 'DOWNLOAD_LIMIT_EXCEEDED'
            }
        
        # Verify program has PDF
        if not purchase.program.pdf_file:
            return {
                'success': False,
                'error': 'Program PDF not available',
                'error_code': 'PDF_NOT_AVAILABLE'
            }
        
        # Get request metadata
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Generate token
        bind_ip = client_ip if self.ENABLE_IP_BINDING else None
        token, raw_token = DownloadToken.generate_token(
            purchase=purchase,
            expires_in_minutes=expires_in,
            max_uses=max_uses,
            bind_ip=bind_ip,
            user_agent=user_agent
        )
        
        # Build download URL
        download_url = self._build_download_url(raw_token)
        
        # Log token generation
        self._log_token_generation(purchase, token, client_ip)
        
        return {
            'success': True,
            'download_url': download_url,
            'token': raw_token,
            'expires_at': token.expires_at.isoformat(),
            'expires_in_seconds': expires_in * 60,
            'remaining_downloads': self.MAX_DOWNLOADS_PER_PURCHASE - purchase.download_count,
        }

    def process_download(
        self,
        raw_token: str,
        request
    ) -> DownloadResult:
        """
        Process a download request with token validation.
        
        Args:
            raw_token: The download token from URL
            request: HTTP request object
            
        Returns:
            DownloadResult with file response or error
        """
        
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Validate token
        is_valid, token_or_error = DownloadToken.validate_token(raw_token, client_ip)
        
        if not is_valid:
            self._log_download_failure(None, client_ip, token_or_error)
            return DownloadResult(
                success=False,
                error_message=token_or_error,
                error_code='TOKEN_INVALID'
            )
        
        token = token_or_error
        purchase = token.purchase
        program = purchase.program
        
        # Verify file exists
        if not program.pdf_file or not default_storage.exists(program.pdf_file.name):
            self._log_download_failure(purchase, client_ip, "File not found on storage")
            return DownloadResult(
                success=False,
                error_message='File not found',
                error_code='FILE_NOT_FOUND'
            )
        
        # Verify file integrity (optional - can be slow for large files)
        if program.pdf_file_hash:
            if not self._verify_file_integrity(program):
                self._log_download_failure(purchase, client_ip, "File integrity check failed")
                return DownloadResult(
                    success=False,
                    error_message='File integrity error',
                    error_code='INTEGRITY_ERROR'
                )
        
        # Mark token as used
        token.mark_used(ip_address=client_ip, user_agent=user_agent)
        
        # Increment purchase download count
        purchase.increment_download(ip_address=client_ip)
        
        # Log successful download
        self._log_download_success(purchase, client_ip)
        
        # Generate file response
        try:
            file_response = self._create_file_response(program)
            return DownloadResult(
                success=True,
                file_response=file_response
            )
        except Exception as e:
            logger.error(f"Error creating file response: {e}")
            return DownloadResult(
                success=False,
                error_message='Error serving file',
                error_code='FILE_ERROR'
            )

    def get_download_status(self, purchase_id: str) -> dict:
        """
        Get download status for a purchase.
        
        Returns:
            Dict with download statistics
        """
        try:
            purchase = Purchase.objects.get(id=purchase_id)
        except Purchase.DoesNotExist:
            return {'error': 'Purchase not found'}
        
        return {
            'purchase_id': str(purchase.id),
            'status': purchase.status,
            'can_download': purchase.can_download,
            'download_count': purchase.download_count,
            'max_downloads': self.MAX_DOWNLOADS_PER_PURCHASE,
            'remaining_downloads': max(0, self.MAX_DOWNLOADS_PER_PURCHASE - purchase.download_count),
            'last_downloaded_at': purchase.last_downloaded_at.isoformat() if purchase.last_downloaded_at else None,
        }

    def revoke_all_tokens(self, purchase_id: str) -> dict:
        """
        Revoke all active download tokens for a purchase.
        
        Useful for:
        - Refund processing
        - Security incidents
        - Admin actions
        """
        try:
            purchase = Purchase.objects.get(id=purchase_id)
        except Purchase.DoesNotExist:
            return {'success': False, 'error': 'Purchase not found'}
        
        revoked_count = DownloadToken.objects.filter(
            purchase=purchase,
            status=DownloadToken.Status.ACTIVE
        ).update(status=DownloadToken.Status.REVOKED)
        
        return {
            'success': True,
            'revoked_count': revoked_count
        }

    # ==================== PRIVATE METHODS ====================

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _build_download_url(self, raw_token: str) -> str:
        """Build the download URL with token"""
        # Adjust based on your URL configuration
        base_url = getattr(settings, 'SITE_URL', 'https://myfita.ir')
        return f"{base_url}/api/programs/download/{raw_token}/"

    def _verify_file_integrity(self, program: Program) -> bool:
        """Verify PDF file hasn't been tampered with"""
        if not program.pdf_file_hash:
            return True  # No hash stored, skip verification
        
        try:
            sha256 = hashlib.sha256()
            for chunk in program.pdf_file.chunks():
                sha256.update(chunk)
            calculated_hash = sha256.hexdigest()
            return calculated_hash == program.pdf_file_hash
        except Exception as e:
            logger.error(f"Error verifying file integrity: {e}")
            return False

    def _create_file_response(self, program: Program) -> FileResponse:
        """Create a secure file response"""
        
        # Generate safe filename
        safe_title = "".join(c for c in program.title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{safe_title[:50]}.pdf"
        
        response = FileResponse(
            program.pdf_file.open('rb'),
            content_type='application/pdf'
        )
        
        # Security headers
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        
        # Prevent embedding in iframes
        response['X-Frame-Options'] = 'DENY'
        
        return response

    def _log_token_generation(self, purchase: Purchase, token: DownloadToken, ip: str):
        """Log token generation for audit"""
        try:
            AuditLog.objects.create(
                action='token_created',
                actor_type='athlete',
                actor_id=str(purchase.athlete_id),
                target_id=purchase.id,
                result='success',
                request_summary={
                    'action': 'download_token_generated',
                    'purchase_id': str(purchase.id),
                    'program_id': str(purchase.program_id),
                    'token_id': str(token.id),
                    'expires_at': token.expires_at.isoformat(),
                    'ip': ip,
                }
            )
        except Exception as e:
            logger.error(f"Error logging token generation: {e}")

    def _log_download_success(self, purchase: Purchase, ip: str):
        """Log successful download for audit"""
        try:
            AuditLog.objects.create(
                action='token_used',
                actor_type='athlete',
                actor_id=str(purchase.athlete_id),
                target_id=purchase.id,
                result='success',
                request_summary={
                    'action': 'pdf_downloaded',
                    'purchase_id': str(purchase.id),
                    'program_id': str(purchase.program_id),
                    'download_count': purchase.download_count,
                    'ip': ip,
                }
            )
        except Exception as e:
            logger.error(f"Error logging download success: {e}")

    def _log_download_failure(self, purchase: Optional[Purchase], ip: str, reason: str):
        """Log failed download attempt for security monitoring"""
        try:
            AuditLog.objects.create(
                action='token_validation_failed',
                actor_type='unknown',
                actor_id=str(purchase.athlete_id) if purchase else None,
                target_id=purchase.id if purchase else None,
                result='failure',
                error_message=reason,
                request_summary={
                    'action': 'download_failed',
                    'reason': reason,
                    'ip': ip,
                }
            )
        except Exception as e:
            logger.error(f"Error logging download failure: {e}")