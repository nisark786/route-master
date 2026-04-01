from rest_framework import serializers


class DriverAssignmentInventoryItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class DriverAssignmentInventoryUpdateSerializer(serializers.Serializer):
    items = DriverAssignmentInventoryItemSerializer(many=True, required=False, default=list)

    def validate_items(self, value):
        product_ids = [str(item["product_id"]) for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Duplicate products are not allowed.")
        return value
