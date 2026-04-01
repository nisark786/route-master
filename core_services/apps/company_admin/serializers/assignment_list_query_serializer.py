from rest_framework import serializers


class AssignmentListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        required=False,
        choices=["all", "ASSIGNED", "IN_ROUTE", "COMPLETED", "CANCELLED"],
        default="all",
    )
