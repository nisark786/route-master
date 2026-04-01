from rest_framework import serializers

from apps.company_admin.models import Product


class ProductSerializer(serializers.ModelSerializer):
    image_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "image",
            "image_key",
            "quantity_count",
            "rate",
            "description",
            "shelf_life",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Product name must be at least 2 characters.")
        return cleaned

    def validate_description(self, value):
        return value.strip()

    def validate_shelf_life(self, value):
        return value.strip()

    def validate_quantity_count(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity count cannot be negative.")
        return value

    def validate_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Rate cannot be negative.")
        return value

    def validate_image(self, value):
        if not value:
            return value
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Image size must be 5MB or less.")
        content_type = getattr(value, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise serializers.ValidationError("Uploaded file must be an image.")
        return value

    def validate_image_key(self, value):
        cleaned = value.strip()
        if not cleaned:
            return ""
        request = self.context.get("request")
        company_id = str(getattr(getattr(request, "user", None), "company_id", "") or "")
        if not company_id:
            raise serializers.ValidationError("Unable to validate image key without company context.")
        expected_prefix = f"products/company-{company_id}/"
        if not cleaned.startswith(expected_prefix):
            raise serializers.ValidationError("Image key is not valid for this company product upload.")
        return cleaned

    def create(self, validated_data):
        image_key = validated_data.pop("image_key", "")
        product = super().create(validated_data)
        if image_key:
            product.image = image_key
            product.save(update_fields=["image", "updated_at"])
        return product

    def update(self, instance, validated_data):
        image_key = validated_data.pop("image_key", "")
        product = super().update(instance, validated_data)
        if image_key:
            product.image = image_key
            product.save(update_fields=["image", "updated_at"])
        return product
