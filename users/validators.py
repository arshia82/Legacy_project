# users/validators.py
"""
Validation utilities for verification system
"""
import re
import magic
from django.core.exceptions import ValidationError
from django.conf import settings


def validate_phone_iran(phone: str) -> str:
    """Validate Iranian phone number format."""
    phone = re.sub(r'\D', '', phone)  # Remove non-digits
    
    if phone.startswith('98'):
        phone = '0' + phone[2:]
    elif phone.startswith('+98'):
        phone = '0' + phone[3:]
    
    if not re.match(r'^09\d{9}$', phone):
        raise ValidationError('Invalid Iranian phone number')
    
    return phone


def validate_document_file(file) -> None:
    """Validate uploaded document file."""
    # Size check (5MB)
    max_size = getattr(settings, 'VERIFICATION_SETTINGS', {}).get('MAX_FILE_SIZE_MB', 5) * 1024 * 1024
    if file.size > max_size:
        raise ValidationError(f'File too large. Max {max_size // (1024*1024)}MB')
    
    # Extension check
    ext = file.name.split('.')[-1].lower()
    allowed = ['pdf', 'jpg', 'jpeg', 'png', 'webp']
    if ext not in allowed:
        raise ValidationError(f'Invalid file type. Allowed: {", ".join(allowed)}')
    
    # MIME type check (using python-magic)
    try:
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)  # Reset file pointer
        
        valid_mimes = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'webp': 'image/webp'
        }
        
        if mime != valid_mimes.get(ext):
            raise ValidationError('File content does not match extension')
    except ImportError:
        pass  # python-magic not installed, skip deep check


def validate_specializations(specs: list) -> list:
    """Validate and clean specializations list."""
    if not isinstance(specs, list):
        raise ValidationError('Specializations must be a list')
    
    cleaned = []
    for s in specs[:10]:  # Max 10
        if isinstance(s, str) and s.strip():
            cleaned.append(s.strip().lower())
    
    return cleaned