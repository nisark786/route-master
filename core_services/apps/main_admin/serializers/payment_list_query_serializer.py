from rest_framework import serializers

from .pagination_query_serializer import PaginationQuerySerializer


class PaymentListQuerySerializer(PaginationQuerySerializer):
    search = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        required=False,
        choices=["all", "SUCCESS", "FAILED", "REFUNDED", "DISPUTED"],
        default="all",
    )
