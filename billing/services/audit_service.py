# billing/services/audit_service.py
from ..models import AuditLog


class AuditService:
    def log(
        self,
        action,
        actor_type,
        result,
        actor_id=None,
        request_summary=None,
        gross_amount=None,
        commission_amount=None,
        net_amount=None,
        error_message=None,
    ):
        return AuditLog.objects.create(
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            request_summary=request_summary or {},
            gross_amount=gross_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            result=result,
            error_message=error_message,
        )

    def verify_chain_integrity(self):
        """
        Verifies audit log hash chain.
        Returns (is_valid: bool, broken_entry: AuditLog | None)
        """
        logs = AuditLog.objects.order_by("created_at")
        previous_hash = "genesis"

        for entry in logs:
            if entry.previous_hash != previous_hash:
                return False, entry

            if entry.entry_hash != entry.compute_hash():
                return False, entry

            previous_hash = entry.entry_hash

        return True, None