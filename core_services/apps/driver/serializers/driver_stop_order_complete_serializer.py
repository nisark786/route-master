from rest_framework import serializers


class DriverStopOrderItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class DriverStopOrderCompleteSerializer(serializers.Serializer):
    items = DriverStopOrderItemSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one ordered item is required.")
        product_ids = [str(item["product_id"]) for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Duplicate products are not allowed.")
        return value
