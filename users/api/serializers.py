"""
API Serializers for authentication.
"""
from rest_framework import serializers
from users.models import User


class OTPSendSerializer(serializers.Serializer):
    """Serializer for OTP send request."""
    
    phone = serializers.CharField(max_length=15)
    purpose = serializers.ChoiceField(
        choices=["login", "register", "reset", "verify"],
        default="login",
        required=False,
    )
    
    def validate_phone(self, value):
        """Validate and normalize phone number."""
        phone = value.strip()
        
        # Remove + prefix
        if phone.startswith("+"):
            phone = phone[1:]
        
        # Convert 989 to 09 format
        if phone.startswith("989") and len(phone) == 12:
            phone = "0" + phone[2:]
        
        # Validate format
        if len(phone) != 11 or not phone.startswith("09") or not phone.isdigit():
            raise serializers.ValidationError("Invalid phone format. Use: 09xxxxxxxxx")
        
        return phone


class OTPVerifySerializer(serializers.Serializer):
    """Serializer for OTP verification request."""
    
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(min_length=6, max_length=6)
    purpose = serializers.ChoiceField(
        choices=["login", "register", "reset", "verify"],
        default="login",
        required=False,
    )
    
    def validate_phone(self, value):
        """Validate and normalize phone number."""
        phone = value.strip()
        if phone.startswith("+"):
            phone = phone[1:]
        if phone.startswith("989") and len(phone) == 12:
            phone = "0" + phone[2:]
        if len(phone) != 11 or not phone.startswith("09") or not phone.isdigit():
            raise serializers.ValidationError("Invalid phone format. Use: 09xxxxxxxxx")
        return phone
    
    def validate_otp(self, value):
        """Validate OTP format."""
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits")
        return value


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""
    
    class Meta:
        model = User
        fields = ["id", "phone", "full_name", "role", "is_phone_verified", "date_joined"]
        read_only_fields = fields
# users/api/serializers.py
"""
Serializers for Coach Verification System

What are Serializers?
- Convert complex data (models) to JSON and vice versa
- Validate incoming data
- Control what fields are exposed in API responses

Kavenegar API Key:
"""
from kavenegar import *
api = KavenegarAPI('6B78587A63766E58546B554549305A71685276414E5950506D687454776B43624744666C34647A6D3042593D')
params = { 'sender' : '2000660110', 'receptor': '09031517191', 'message' :'.My FITA is AT YOUR SERVICE' }

from rest_framework import serializers
from django.conf import settings
from users.models import (
    User,
    CoachVerificationRequest,
    VerificationDocument,
    VerificationStatusLog
)


# ============================================================
# USER SERIALIZERS
# ============================================================

class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user info for embedding in other serializers.
    Used when we need to show who submitted/reviewed a request.
    """
    
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'first_name', 'last_name', 'full_name', 'role', 'is_verified']
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full user profile for the authenticated user.
    Includes verification status and other details.
    """
    
    full_name = serializers.CharField(read_only=True)
    can_submit_verification = serializers.SerializerMethodField()
    active_verification = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_verified', 'verified_at', 'bio', 'profile_image',
            'date_joined', 'can_submit_verification', 'active_verification'
        ]
        read_only_fields = ['id', 'phone', 'is_verified', 'verified_at', 'date_joined']
    
    def get_can_submit_verification(self, obj) -> bool:
        """Check if user can submit a new verification request."""
        return obj.can_submit_verification()
    
    def get_active_verification(self, obj) -> dict:
        """Get user's active verification request if any."""
        active = obj.verification_requests.filter(
            status__in=['draft', 'pending', 'under_review', 'needs_info']
        ).first()
        
        if active:
            return {
                'id': active.id,
                'request_number': active.request_number,
                'status': active.status,
                'submitted_at': active.submitted_at
            }
        return None


# ============================================================
# DOCUMENT SERIALIZERS
# ============================================================

class VerificationDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for verification documents.
    Handles file uploads and validation.
    """
    
    file_size_display = serializers.CharField(read_only=True)
    is_image = serializers.BooleanField(read_only=True)
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = VerificationDocument
        fields = [
            'id', 'document_type', 'document_type_display',
            'file', 'original_filename', 'file_size', 'file_size_display',
            'mime_type', 'is_image', 'status', 'status_display',
            'rejection_reason', 'description', 'uploaded_at'
        ]
        read_only_fields = [
            'id', 'original_filename', 'file_size', 'mime_type',
            'status', 'rejection_reason', 'uploaded_at'
        ]
    
    def validate_file(self, value):
        """
        Validate uploaded file.
        
        Checks:
        1. File size within limit
        2. File extension allowed
        3. MIME type matches extension (basic check)
        """
        # Check file size
        max_size = settings.VERIFICATION_SETTINGS.get('MAX_FILE_SIZE_MB', 5) * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {max_size // (1024*1024)} MB."
            )
        
        # Check extension
        ext = value.name.split('.')[-1].lower()
        allowed = settings.VERIFICATION_SETTINGS.get(
            'ALLOWED_EXTENSIONS',
            ['pdf', 'jpg', 'jpeg', 'png', 'webp']
        )
        if ext not in allowed:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed)}"
            )
        
        return value
    
    def create(self, validated_data):
        """Create document with metadata."""
        file = validated_data.get('file')
        
        # Store original filename and mime type
        validated_data['original_filename'] = file.name
        validated_data['mime_type'] = file.content_type or 'application/octet-stream'
        validated_data['file_size'] = file.size
        
        return super().create(validated_data)


class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer specifically for document upload endpoint.
    Simpler than full document serializer.
    """
    
    file = serializers.FileField()
    document_type = serializers.ChoiceField(
        choices=VerificationDocument.DocumentType.choices
    )
    description = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_file(self, value):
        """Same validation as VerificationDocumentSerializer."""
        max_size = 5 * 1024 * 1024  # 5 MB
        if value.size > max_size:
            raise serializers.ValidationError("File too large. Maximum 5 MB.")
        
        ext = value.name.split('.')[-1].lower()
        allowed = ['pdf', 'jpg', 'jpeg', 'png', 'webp']
        if ext not in allowed:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed: {', '.join(allowed)}"
            )
        
        return value


# ============================================================
# VERIFICATION REQUEST SERIALIZERS
# ============================================================

class VerificationStatusLogSerializer(serializers.ModelSerializer):
    """Serializer for status change logs."""
    
    changed_by_name = serializers.CharField(
        source='changed_by.full_name',
        read_only=True
    )
    
    class Meta:
        model = VerificationStatusLog
        fields = [
            'id', 'from_status', 'to_status',
            'changed_by', 'changed_by_name', 'changed_at', 'notes'
        ]
        read_only_fields = fields


class CoachVerificationRequestSerializer(serializers.ModelSerializer):
    """
    Full serializer for verification requests.
    Used for detail views and creating/updating requests.
    """
    
    user = UserBasicSerializer(read_only=True)
    reviewed_by = UserBasicSerializer(read_only=True)
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    status_logs = VerificationStatusLogSerializer(many=True, read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_pending = serializers.IntegerField(read_only=True)
    document_count = serializers.IntegerField(read_only=True)
    can_be_edited = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CoachVerificationRequest
        fields = [
            'id', 'request_number', 'user', 'status', 'status_display',
            'created_at', 'updated_at', 'submitted_at', 'reviewed_at',
            'reviewed_by', 'admin_notes', 'rejection_reason', 'info_request_message',
            'coach_message', 'specializations', 'years_experience',
            'documents', 'status_logs', 'days_pending', 'document_count',
            'can_be_edited', 'is_active'
        ]
        read_only_fields = [
            'id', 'request_number', 'user', 'status', 'created_at', 'updated_at',
            'submitted_at', 'reviewed_at', 'reviewed_by', 'admin_notes',
            'rejection_reason', 'info_request_message'
        ]
    
    def validate_specializations(self, value):
        """Validate specializations list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Specializations must be a list")
        
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 specializations allowed")
        
        # Clean and validate each item
        cleaned = []
        for item in value:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip().lower())
        
        return cleaned
    
    def validate_years_experience(self, value):
        """Validate years of experience."""
        if value is not None:
            if value < 0 or value > 50:
                raise serializers.ValidationError(
                    "Years of experience must be between 0 and 50"
                )
        return value


class CoachVerificationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    Excludes heavy fields like documents and logs.
    """
    
    user = UserBasicSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_count = serializers.IntegerField(read_only=True)
    days_pending = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = CoachVerificationRequest
        fields = [
            'id', 'request_number', 'user', 'status', 'status_display',
            'created_at', 'submitted_at', 'document_count', 'days_pending'
        ]


class CreateVerificationRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new verification requests.
    Only allows coach-editable fields.
    """
    
    class Meta:
        model = CoachVerificationRequest
        fields = ['coach_message', 'specializations', 'years_experience']
    
    def validate(self, attrs):
        """Check if user can create a verification request."""
        user = self.context['request'].user
        
        # Check role
        if user.role != 'coach':
            raise serializers.ValidationError(
                "Only coaches can submit verification requests"
            )
        
        # Check if already verified
        if user.is_verified:
            raise serializers.ValidationError(
                "You are already verified"
            )
        
        # Check for existing active request
        active_request = user.verification_requests.filter(
            status__in=['draft', 'pending', 'under_review', 'needs_info']
        ).exists()
        
        if active_request:
            raise serializers.ValidationError(
                "You already have an active verification request"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create verification request for current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================
# ADMIN ACTION SERIALIZERS
# ============================================================

class ApproveVerificationSerializer(serializers.Serializer):
    """Serializer for approval action."""
    
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class RejectVerificationSerializer(serializers.Serializer):
    """Serializer for rejection action."""
    
    reason = serializers.CharField(required=True, min_length=10)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_reason(self, value):
        """Ensure reason is meaningful."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Please provide a detailed reason (at least 10 characters)"
            )
        return value.strip()


class RequestInfoSerializer(serializers.Serializer):
    """Serializer for requesting more information."""
    
    message = serializers.CharField(required=True, min_length=10)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_message(self, value):
        """Ensure message is clear."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Please provide a clear message (at least 10 characters)"
            )
        return value.strip()


class DocumentReviewSerializer(serializers.Serializer):
    """Serializer for reviewing individual documents."""
    
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate(self, attrs):
        """Require reason for rejection."""
        if attrs['action'] == 'reject' and not attrs.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Reason is required when rejecting a document'
            })
        return attrs