from rest_framework import serializers


class RouteShopPositionUpdateSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=1)
