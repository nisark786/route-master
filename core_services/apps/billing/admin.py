from django.contrib import admin

from apps.billing.models import (
    CompanySubscription,
    PaymentTransaction,
    PendingCompanyRegistration,
    PlanChangeLog,
    SubscriptionPlan,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "price", "duration_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(PendingCompanyRegistration)
class PendingCompanyRegistrationAdmin(admin.ModelAdmin):
    list_display = ("company_name", "official_email", "admin_email", "plan", "status", "is_verified", "created_at")
    list_filter = ("status", "is_verified", "plan", "created_at")
    search_fields = ("company_name", "official_email", "admin_email", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "plan",
        "pending_plan",
        "pending_plan_effective_at",
        "amount_paid",
        "currency",
        "start_date",
        "end_date",
        "is_active",
    )
    list_filter = ("is_active", "currency", "plan", "pending_plan")
    search_fields = ("company__name", "company__official_email", "plan__name", "plan__code")
    ordering = ("-start_date",)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("company", "subscription", "provider", "invoice_number", "amount", "currency", "status", "paid_at")
    list_filter = ("status", "provider", "currency", "paid_at")
    search_fields = ("company__name", "company__official_email", "order_id", "payment_id", "invoice_number")
    ordering = ("-paid_at",)


@admin.register(PlanChangeLog)
class PlanChangeLogAdmin(admin.ModelAdmin):
    list_display = ("company", "old_plan", "new_plan", "changed_by", "created_at")
    list_filter = ("created_at", "old_plan", "new_plan")
    search_fields = ("company__name", "company__official_email", "changed_by__email", "reason")
    ordering = ("-created_at",)
