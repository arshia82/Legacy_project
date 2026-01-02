from django.core.exceptions import PermissionDenied


def can_withdraw(user):
    if user.role != "coach":
        raise PermissionDenied("Only coaches can withdraw")

    if not user.is_coach_verified:
        raise PermissionDenied(
            "Coach must be verified before withdrawing funds"
        )

    return True