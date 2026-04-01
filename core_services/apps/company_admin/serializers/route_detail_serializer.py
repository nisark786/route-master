from rest_framework import serializers

from apps.company_admin.models import Route

from .route_shop_assignment_serializer import RouteShopAssignmentSerializer


class RouteDetailSerializer(serializers.ModelSerializer):
    route_shops = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            "id",
            "route_name",
            "start_point",
            "end_point",
            "created_at",
            "updated_at",
            "route_shops",
        ]

    def get_route_shops(self, obj):
        assignments = obj.route_shops.select_related("shop").all().order_by("position")
        return RouteShopAssignmentSerializer(assignments, many=True, context=self.context).data
