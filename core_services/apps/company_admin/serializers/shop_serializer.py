from rest_framework import serializers
from django.contrib.gis.geos import Point

from apps.company_admin.models import Shop


class ShopSerializer(serializers.ModelSerializer):
    point = serializers.SerializerMethodField(read_only=True)
    owner_user_id = serializers.UUIDField(source="owner_user.id", read_only=True)
    image_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "location",
            "location_display_name",
            "latitude",
            "longitude",
            "point",
            "owner_name",
            "owner_mobile_number",
            "owner_user_id",
            "image",
            "image_key",
            "address",
            "landmark",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Shop name must be at least 2 characters.")
        return cleaned

    def validate_owner_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Owner name must be at least 2 characters.")
        return cleaned

    def validate_owner_mobile_number(self, value):
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            return cleaned
        if len(cleaned) < 8:
            raise serializers.ValidationError("Owner mobile number is too short.")
        return cleaned.replace(" ", "").replace("-", "")

    def validate_location(self, value):
        return value.strip()

    def validate_location_display_name(self, value):
        return value.strip()

    def validate_address(self, value):
        return value.strip()

    def validate_landmark(self, value):
        return value.strip()

    def validate_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
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
        expected_prefix = f"shops/company-{company_id}/"
        if not cleaned.startswith(expected_prefix):
            raise serializers.ValidationError("Image key is not valid for this company shop upload.")
        return cleaned

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")

        if latitude is None and instance is not None:
            latitude = instance.latitude
        if longitude is None and instance is not None:
            longitude = instance.longitude

        if latitude is None or longitude is None:
            raise serializers.ValidationError("Latitude and longitude are required.")

        attrs["point"] = Point(float(longitude), float(latitude), srid=4326)
        return attrs

    def get_point(self, obj):
        if not obj.point:
            return None
        return {"type": "Point", "coordinates": [obj.point.x, obj.point.y]}

    def create(self, validated_data):
        image_key = validated_data.pop("image_key", "")
        shop = super().create(validated_data)
        if image_key:
            shop.image = image_key
            shop.save(update_fields=["image", "updated_at"])
        return shop

    def update(self, instance, validated_data):
        image_key = validated_data.pop("image_key", "")
        shop = super().update(instance, validated_data)
        if image_key:
            shop.image = image_key
            shop.save(update_fields=["image", "updated_at"])
        return shop
