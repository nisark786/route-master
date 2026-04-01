from rest_framework import serializers

from apps.company_admin.models import Route


class RouteListItemSerializer(serializers.ModelSerializer):
    shops_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Route
        fields = [
            "id",
            "route_name",
            "start_point",
            "end_point",
            "shops_count",
            "created_at",
            "updated_at",
        ]
