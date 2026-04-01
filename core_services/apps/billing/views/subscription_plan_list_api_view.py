from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.serializers import SubscriptionPlanSerializer
from apps.billing.services import get_cached_active_plans


class SubscriptionPlanListAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="List subscription plans",
        operation_description="Fetch active subscription plans for company onboarding.",
        responses={200: SubscriptionPlanSerializer(many=True)},
    )
    def get(self, request):
        plans = get_cached_active_plans()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
