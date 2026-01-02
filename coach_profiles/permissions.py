from rest_framework.permissions import BasePermission


class IsCoach(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "coach"


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff