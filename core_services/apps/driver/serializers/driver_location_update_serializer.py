from rest_framework import serializers


class DriverLocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    speed_kph = serializers.FloatField(required=False, default=0, min_value=0)
    heading = serializers.FloatField(required=False, default=0, min_value=0, max_value=360)
    captured_at = serializers.DateTimeField(required=False)
