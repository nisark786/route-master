from django.contrib import admin

from apps.driver.models import DriverRouteRun, DriverRunStop


@admin.register(DriverRouteRun)
class DriverRouteRunAdmin(admin.ModelAdmin):
    list_display = ("assignment", "driver", "route", "vehicle", "status", "started_at", "completed_at")
    list_filter = ("status", "driver__user__company")
    search_fields = ("driver__name", "route__route_name", "vehicle__name")
    ordering = ("-started_at",)


@admin.register(DriverRunStop)
class DriverRunStopAdmin(admin.ModelAdmin):
    list_display = ("run", "shop", "position", "status", "check_in_at", "check_out_at", "invoice_number")
    list_filter = ("status", "run__driver__user__company")
    search_fields = ("shop__name", "shop__owner_name", "invoice_number")
    ordering = ("run", "position")
