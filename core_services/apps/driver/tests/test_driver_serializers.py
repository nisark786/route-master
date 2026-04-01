import pytest

from apps.driver.serializers import DriverLocationUpdateSerializer


def test_driver_location_update_serializer_defaults_optional_fields():
    serializer = DriverLocationUpdateSerializer(
        data={"latitude": 12.97, "longitude": 77.59}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["speed_kph"] == 0
    assert serializer.validated_data["heading"] == 0


def test_driver_location_update_serializer_rejects_invalid_heading():
    serializer = DriverLocationUpdateSerializer(
        data={"latitude": 12.97, "longitude": 77.59, "heading": 361}
    )

    assert not serializer.is_valid()
    assert "heading" in serializer.errors
