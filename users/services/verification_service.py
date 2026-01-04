# users/services/verification_service.py

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone

from users.models import (
    CoachVerificationRequest,
    VerificationDocument,
    VerificationStatusLog,
)

DRAFT = "draft"
PENDING = "pending"  # ✅ ADDED (tests import this)
SUBMITTED = "submitted"
APPROVED = "approved"
REJECTED = "rejected"

from users.services.business_rules import (
    generate_trust_token,
    validate_trust_token,
) 

class VerificationService:
    """
    Service layer for coach verification logic.
    Enforces security, permissions, and state transitions.
    """

    def create_request(self, user):
        """
        Create a new verification request.
        TEST 09: Only coaches can create.
        """
        if user.role != "coach":
            raise ValidationError("Only coaches can create verification requests.")

        try:
            with transaction.atomic():
                return CoachVerificationRequest.objects.create(
                    user=user,
                    is_active=True,
                )
        except IntegrityError:
            raise ValidationError("An active verification request already exists.")

    def submit_request(self, request, user):
        """
        Submit a draft request for admin review.
        TEST 03/14: Ownership check.
        TEST 17: Cannot submit twice.
        TEST 30: Concurrent submission safe.
        """
        if request.user != user:
            raise ValidationError("You cannot submit another user's request.")

        with transaction.atomic():
            locked = (
                CoachVerificationRequest.objects
                .select_for_update()
                .get(pk=request.pk)
            )

            if locked.status != DRAFT:
                raise ValidationError("Only draft requests can be submitted.")

            locked.status = SUBMITTED
            locked.updated_at = timezone.now()
            locked.save(update_fields=["status", "updated_at"])

            VerificationStatusLog.objects.create(
                verification_request=locked,
                from_status=DRAFT,
                to_status=SUBMITTED,
            )

            return locked

    def approve_request(self, request, admin_user):
        """
        Approve a verification request.
        TEST 04/08: Only admin can approve.
        TEST 16: Auto-submit if draft (admin workflow).
        TEST 31: Concurrent approval idempotent.
        """
        if not admin_user.is_staff or admin_user.role != "admin":
            raise ValidationError("Only admins can approve verification requests.")

        with transaction.atomic():
            locked = (
                CoachVerificationRequest.objects
                .select_for_update()
                .get(pk=request.pk)
            )

            # ✅ Idempotent: already approved
            if locked.status == APPROVED:
                return locked

            # ✅ TEST 16: Admin can approve from DRAFT (auto-submit)
            if locked.status == DRAFT:
                locked.status = SUBMITTED
                VerificationStatusLog.objects.create(
                    verification_request=locked,
                    from_status=DRAFT,
                    to_status=SUBMITTED,
                )

            # ✅ Now approve
            if locked.status != SUBMITTED:
                raise ValidationError("Only submitted requests can be approved.")

            old_status = locked.status
            locked.status = APPROVED
            locked.is_active = False
            locked.updated_at = timezone.now()
            locked.save(update_fields=["status", "is_active", "updated_at"])

            # ✅ Verify coach
            coach = locked.user
            coach.is_verified = True
            coach.save(update_fields=["is_verified"])

            VerificationStatusLog.objects.create(
                verification_request=locked,
                from_status=old_status,
                to_status=APPROVED,
            )

            return locked

    def add_document(self, request, file, doc_type, user):
        """
        Add a document to a verification request.
        TEST 10: Cross-user access blocked.
        """
        if request.user != user:
            raise ValidationError("You cannot add documents to another user's request.")

        return VerificationDocument.objects.create(
            verification_request=request,
            document_type=doc_type,
            file=file,
            original_filename=getattr(file, "name", ""),
        )

    def get_pending_requests(self):
        """
        Get all submitted requests awaiting admin review.
        """
        return CoachVerificationRequest.objects.filter(
            status=SUBMITTED,
            is_active=True,
        ).order_by("created_at")

    def can_coach_be_visible(self, coach):
        """
        Determine if coach can appear in marketplace.
        TEST 20: Only verified coaches visible.
        Business Plan §6.10: Trust system.
        """
        return bool(coach.is_verified)


verification_service = VerificationService()