from django.contrib import admin

from apps.company_admin.models import Driver, DriverAssignment, Product, Route, RouteShop, Shop, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "number_plate", "company", "status", "fuel_percentage", "created_at")
    list_filter = ("status", "company", "created_at")
    search_fields = ("name", "number_plate", "company__name", "company__official_email")
    ordering = ("-created_at",)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner_name",
        "owner_mobile_number",
        "owner_user",
        "company",
        "location_display_name",
        "latitude",
        "longitude",
        "created_at",
    )
    list_filter = ("company", "created_at")
    search_fields = (
        "name",
        "owner_name",
        "owner_mobile_number",
        "owner_user__mobile_number",
        "location",
        "location_display_name",
        "address",
        "landmark",
        "company__name",
    )
    ordering = ("-created_at",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("route_name", "company", "start_point", "end_point", "created_at")
    list_filter = ("company", "created_at")
    search_fields = ("route_name", "start_point", "end_point", "company__name")
    ordering = ("-created_at",)


@admin.register(RouteShop)
class RouteShopAdmin(admin.ModelAdmin):
    list_display = ("route", "shop", "position", "created_at")
    list_filter = ("route__company", "route", "created_at")
    search_fields = ("route__route_name", "shop__name", "shop__owner_name")
    ordering = ("route", "position")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "get_mobile_number", "age", "status", "get_company", "created_at")
    list_filter = ("user__company", "status", "created_at")
    search_fields = ("name", "user__mobile_number", "user__company__name")
    ordering = ("-created_at",)

    @admin.display(ordering="user__mobile_number", description="Mobile Number")
    def get_mobile_number(self, obj):
        return obj.user.mobile_number

    @admin.display(ordering="user__company", description="Company")
    def get_company(self, obj):
        return obj.user.company


@admin.register(DriverAssignment)
class DriverAssignmentAdmin(admin.ModelAdmin):
    list_display = ("driver", "route", "vehicle", "scheduled_at", "status", "created_at")
    list_filter = ("driver__user__company", "status", "scheduled_at")
    search_fields = ("driver__name", "driver__user__mobile_number", "route__route_name", "vehicle__name", "vehicle__number_plate")
    ordering = ("-scheduled_at",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "quantity_count", "rate", "shelf_life", "created_at")
    list_filter = ("company", "created_at")
    search_fields = ("name", "description", "shelf_life", "company__name")
    ordering = ("-created_at",)
