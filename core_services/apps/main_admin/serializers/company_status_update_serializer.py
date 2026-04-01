from rest_framework import serializers


class CompanyStatusUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["suspend", "reactivate"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")
