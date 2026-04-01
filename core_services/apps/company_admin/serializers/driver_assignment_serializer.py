from rest_framework import serializers
from django.utils import timezone

from apps.company_admin.models import DriverAssignment


class DriverAssignmentSerializer(serializers.ModelSerializer):
    driver = serializers.UUIDField(source="driver_id", read_only=True)
    driver_name = serializers.CharField(source="driver.name", read_only=True)
    driver_mobile_number = serializers.CharField(source="driver.user.mobile_number", read_only=True)
    route_name = serializers.CharField(source="route.route_name", read_only=True)
    vehicle_name = serializers.CharField(source="vehicle.name", read_only=True)
    vehicle_number_plate = serializers.CharField(source="vehicle.number_plate", read_only=True)

    class Meta:
        model = DriverAssignment
        fields = [
            "id",
            "driver",
            "driver_name",
            "driver_mobile_number",
            "route",
            "vehicle",
            "route_name",
            "vehicle_name",
            "vehicle_number_plate",
            "scheduled_at",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "driver",
            "driver_name",
            "driver_mobile_number",
            "route_name",
            "vehicle_name",
            "vehicle_number_plate",
        ]

    def validate_notes(self, value):
        return value.strip()

    def validate_scheduled_at(self, value):
        if timezone.is_naive(value):
            raise serializers.ValidationError("scheduled_at must include timezone information.")
        return value
