from rest_framework import serializers


class MediaUploadRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["product", "shop"])
    file_name = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120)
    file_size = serializers.IntegerField(min_value=1, max_value=5 * 1024 * 1024)

    def validate_file_name(self, value):
        cleaned = value.strip()
        if "." not in cleaned:
            raise serializers.ValidationError("File name must include an extension.")
        return cleaned

    def validate_content_type(self, value):
        cleaned = value.strip().lower()
        if not cleaned.startswith("image/"):
            raise serializers.ValidationError("Only image uploads are supported.")
        return cleaned
