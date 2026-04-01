from rest_framework import serializers

from .route_shop_input_serializer import RouteShopInputSerializer


class RouteCreateSerializer(serializers.Serializer):
    route_name = serializers.CharField(max_length=120)
    start_point = serializers.CharField(max_length=255)
    end_point = serializers.CharField(max_length=255)
    shops = RouteShopInputSerializer(many=True, required=False, default=list)

    def validate_route_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Route name must be at least 2 characters.")
        return cleaned

    def validate_start_point(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Start point must be at least 2 characters.")
        return cleaned

    def validate_end_point(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("End point must be at least 2 characters.")
        return cleaned
