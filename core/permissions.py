# FILE: myfita/apps/backend/core/permissions.py

"""
CUSTOM PERMISSIONS

Reusable permission classes for API views.
"""

from rest_framework.permissions import BasePermission


class IsCoach(BasePermission):
    """
    Permission check for coach users.
    """
    
    message = "فقط مربیان به این بخش دسترسی دارند."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == "coach"
        )


class IsAthlete(BasePermission):
    """
    Permission check for athlete users.
    """
    
    message = "فقط ورزشکاران به این بخش دسترسی دارند."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == "athlete"
        )


class IsAdmin(BasePermission):
    """
    Permission check for admin users.
    """
    
    message = "فقط مدیران به این بخش دسترسی دارند."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == "admin"
        )


class IsVerifiedCoach(BasePermission):
    """
    Permission check for verified coach users.
    
    BP: "admin verification workflow aims for verified status within 12 hours"
    """
    
    message = "فقط مربیان تایید شده به این بخش دسترسی دارند."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == "coach" and
            getattr(request.user, "is_verified", False)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Permission check for object owner or admin.
    
    Requires the view to have a get_object() method.
    """
    
    message = "شما اجازه دسترسی به این منبع را ندارید."
    
    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if request.user.role == "admin":
            return True
        
        # Check ownership
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        if hasattr(obj, "coach"):
            return obj.coach == request.user
        if hasattr(obj, "athlete"):
            return obj.athlete == request.user
        
        return False


class IsCoachOrReadOnly(BasePermission):
    """
    Coaches can modify, others can only read.
    """
    
    def has_permission(self, request, view):
        # Allow read operations for everyone
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        
        # Write operations require coach role
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == "coach"
        )


class IsProgramOwner(BasePermission):
    """
    Check if user owns the program.
    """
    
    message = "شما مالک این برنامه نیستید."
    
    def has_object_permission(self, request, view, obj):
        return obj.coach == request.user


class HasPurchasedProgram(BasePermission):
    """
    Check if user has purchased the program.
    
    BP: "program purchase delivery (PDF)"
    """
    
    message = "شما این برنامه را خریداری نکرده‌اید."
    
    def has_object_permission(self, request, view, obj):
        from billing.models import Purchase
        
        # Coach always has access to their own programs
        if hasattr(obj, "coach") and obj.coach == request.user:
            return True
        
        # Check for purchase
        program_id = obj.id if hasattr(obj, "id") else obj
        
        return Purchase.objects.filter(
            athlete=request.user,
            program_id=program_id,
            status="completed"
        ).exists()