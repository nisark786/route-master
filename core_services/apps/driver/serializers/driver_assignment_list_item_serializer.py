from rest_framework import serializers

from apps.company_admin.models import DriverAssignment


class DriverAssignmentListItemSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source="route.route_name", read_only=True)
    start_point = serializers.CharField(source="route.start_point", read_only=True)
    end_point = serializers.CharField(source="route.end_point", read_only=True)
    vehicle_name = serializers.CharField(source="vehicle.name", read_only=True)
    vehicle_number_plate = serializers.CharField(source="vehicle.number_plate", read_only=True)
    shops_count = serializers.SerializerMethodField()

    class Meta:
        model = DriverAssignment
        fields = [
            "id",
            "route",
            "route_name",
            "start_point",
            "end_point",
            "vehicle",
            "vehicle_name",
            "vehicle_number_plate",
            "scheduled_at",
            "status",
            "notes",
            "shops_count",
        ]

    def get_shops_count(self, obj):
        return obj.route.route_shops.count()
