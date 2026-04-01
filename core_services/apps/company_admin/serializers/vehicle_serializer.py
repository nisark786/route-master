import re

from rest_framework import serializers

from apps.company_admin.models import Vehicle


NUMBER_PLATE_PATTERN = re.compile(r"^[A-Z0-9 -]{3,20}$")


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "id",
            "name",
            "number_plate",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        name = value.strip()
        if len(name) < 2:
            raise serializers.ValidationError("Vehicle name must be at least 2 characters.")
        return name

    def validate_number_plate(self, value):
        plate = re.sub(r"\s+", " ", value.strip().upper())
        if not NUMBER_PLATE_PATTERN.match(plate):
            raise serializers.ValidationError(
                "Number plate must be 3-20 chars and contain only letters, digits, spaces, or '-'."
            )
        return plate
