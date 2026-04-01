from django.contrib import admin

from apps.company.models import Company, CompanyActivityLog


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "official_email",
        "operational_status",
        "is_active",
        "is_email_verified",
        "created_at",
    )
    list_filter = ("operational_status", "is_active", "is_email_verified", "created_at")
    search_fields = ("name", "official_email", "phone")
    ordering = ("-created_at",)


@admin.register(CompanyActivityLog)
class CompanyActivityLogAdmin(admin.ModelAdmin):
    list_display = ("company", "actor", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("company__name", "actor__email", "action")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
