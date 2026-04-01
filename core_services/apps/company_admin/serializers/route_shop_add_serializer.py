from rest_framework import serializers


class RouteShopAddSerializer(serializers.Serializer):
    shop_id = serializers.UUIDField()
    position = serializers.IntegerField(required=False, min_value=1)
