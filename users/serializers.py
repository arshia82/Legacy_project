from rest_framework import serializers


class RequestOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    role = serializers.ChoiceField(choices=["athlete", "coach", "admin"])


class VerifyOTPSerializer(serializers.Serializer):
    otp_id = serializers.UUIDField()
    code = serializers.CharField(max_length=6)
from rest_framework import serializers
from .models import CoachVerificationRequest


class CoachVerificationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachVerificationRequest
        fields = [
            "full_name",
            "national_id",
            "certificate_image",
            "profile_photo",
        ]
# users/serializers.py
"""
OTP Serializers with validation.
"""

import re
from rest_framework import serializers


class SendOTPSerializer(serializers.Serializer):
    """Serializer for OTP send request."""
    
    phone = serializers.CharField(max_length=15, min_length=10)
    
    def validate_phone(self, value):
        """Validate Iranian phone number format."""
        # Remove spaces and dashes
        phone = value.strip().replace(' ', '').replace('-', '')
        
        # Normalize to 09XXXXXXXXX format
        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('98'):
            phone = '0' + phone[2:]
        elif phone.startswith('9') and len(phone) == 10:
            phone = '0' + phone
        
        # Validate format
        if not re.match(r'^09\d{9}$', phone):
            raise serializers.ValidationError("Invalid phone number format.")
        
        return phone


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for OTP verification."""
    
    phone = serializers.CharField(max_length=15, min_length=10)
    code = serializers.CharField(max_length=6, min_length=6)
    
    def validate_phone(self, value):
        """Validate and normalize phone number."""
        phone = value.strip().replace(' ', '').replace('-', '')
        
        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('98'):
            phone = '0' + phone[2:]
        elif phone.startswith('9') and len(phone) == 10:
            phone = '0' + phone
        
        if not re.match(r'^09\d{9}$', phone):
            raise serializers.ValidationError("Invalid phone number format.")
        
        return phone
    
    def validate_code(self, value):
        """Validate OTP code format."""
        code = value.strip()
        
        if not code.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        
        if len(code) != 6:
            raise serializers.ValidationError("OTP must be exactly 6 digits.")
        
        return code