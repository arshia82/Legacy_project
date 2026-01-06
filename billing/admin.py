# billing/admin.py
"""
Django admin configuration for billing models.
CFO-friendly dashboards for commission, payouts, audit, and disintermediation risk.
"""

import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    CommissionConfig,
    TrustToken,
    Payout,
    AuditLog,
    DisintermediationAlert,
)

# ============================================================================
# COMMON ACTIONS
# ============================================================================

def export_as_csv(modeladmin, request, queryset):
    """Export selected rows to CSV."""
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{meta.model_name}.csv"'
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])

    return response


export_as_csv.short_description = "Export selected to CSV"


# ============================================================================
# COMMISSION CONFIG
# ============================================================================

@admin.register(CommissionConfig)
class CommissionConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "rate", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["-is_active", "-created_at"]
    actions = [export_as_csv]

    def save_model(self, request, obj, form, change):
        """Ensure only one active commission config."""
        if obj.is_active:
            CommissionConfig.objects.filter(is_active=True).exclude(id=obj.id).update(
                is_active=False
            )
        super().save_model(request, obj, form, change)


# ============================================================================
# TRUST TOKENS
# ============================================================================

@admin.register(TrustToken)
class TrustTokenAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "coach_short",
        "athlete_short",
        "gross_toman",
        "commission_toman",
        "net_toman",
        "status_badge",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "coach_id", "athlete_id", "idempotency_key"]
    readonly_fields = [
        "id",
        "integrity_hash",
        "created_at",
        "expires_at",
        "used_at",
    ]
    ordering = ["-created_at"]
    actions = [export_as_csv]

    fieldsets = (
        ("Identifiers", {"fields": ("id", "status", "idempotency_key")}),
        ("Parties", {"fields": ("program_id", "coach_id", "athlete_id")}),
        ("Financials", {
            "fields": (
                "gross_amount",
                "commission_amount",
                "net_amount",
                "commission_rate",
            )
        }),
        ("Security", {"fields": ("integrity_hash",)}),
        ("Timestamps", {"fields": ("created_at", "expires_at", "used_at")}),
    )

    def coach_short(self, obj):
        return str(obj.coach_id)[:8]
    coach_short.short_description = "Coach"

    def athlete_short(self, obj):
        return str(obj.athlete_id)[:8]
    athlete_short.short_description = "Athlete"

    def gross_toman(self, obj):
        return f"{obj.gross_amount / 100:,.0f} ﷼"
    gross_toman.short_description = "Gross"

    def commission_toman(self, obj):
        return f"{obj.commission_amount / 100:,.0f} ﷼"
    commission_toman.short_description = "Commission"

    def net_toman(self, obj):
        return f"{obj.net_amount / 100:,.0f} ﷼"
    net_toman.short_description = "Net"

    def status_badge(self, obj):
        colors = {
            TrustToken.Status.ACTIVE: "green",
            TrustToken.Status.USED: "blue",
            TrustToken.Status.EXPIRED: "orange",
            TrustToken.Status.REVOKED: "red",
        }
        return format_html(
            '<b style="color:{}">{}</b>',
            colors.get(obj.status, "black"),
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"


# ============================================================================
# PAYOUTS
# ============================================================================

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "coach",
        "net_toman",
        "commission_toman",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "coach__phone"]
    readonly_fields = [
        "id",
        "trust_token",
        "gross_amount",
        "commission_amount",
        "net_amount",
        "commission_rate",
        "created_at",
    ]
    ordering = ["-created_at"]
    actions = [export_as_csv]

    def net_toman(self, obj):
        return f"{obj.net_amount / 100:,.0f} ﷼"
    net_toman.short_description = "Net"

    def commission_toman(self, obj):
        return f"{obj.commission_amount / 100:,.0f} ﷼"
    commission_toman.short_description = "Commission"


# ============================================================================
# AUDIT LOG (IMMUTABLE)
# ============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "action",
        "actor_type",
        "actor_id_short",
        "result_badge",
        "created_at",
    ]
    list_filter = ["action", "actor_type", "result"]
    search_fields = ["id", "actor_id"]
    readonly_fields = [
        "id",
        "action",
        "actor_type",
        "actor_id",
        "request_summary",
        "gross_amount",
        "commission_amount",
        "net_amount",
        "result",
        "error_message",
        "previous_hash",
        "entry_hash",
        "created_at",
    ]
    ordering = ["-created_at"]
    actions = [export_as_csv]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def actor_id_short(self, obj):
        return obj.actor_id[:8] if obj.actor_id else "—"
    actor_id_short.short_description = "Actor"

    def result_badge(self, obj):
        colors = {
            "success": "green",
            "rejected": "red",
            "failed": "orange",
        }
        return format_html(
            '<b style="color:{}">{}</b>',
            colors.get(obj.result, "black"),
            obj.result.upper(),
        )
    result_badge.short_description = "Result"


# ============================================================================
# DISINTERMEDIATION ALERTS (MINIMAL & SAFE)
# ============================================================================

@admin.register(DisintermediationAlert)
class DisintermediationAlertAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "coach",
        "alert_type",
        "severity",
        "is_resolved",
        "created_at",
    ]
    list_filter = ["alert_type", "severity", "is_resolved"]
    search_fields = ["coach__phone", "description"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]
    actions = [export_as_csv]


# ============================================================================
# ADMIN BRANDING
# ============================================================================

admin.site.site_header = "MY FITA – Billing & Compliance"
admin.site.site_title = "MY FITA Admin"
admin.site.index_title = "Commission, Payouts & Risk Management"