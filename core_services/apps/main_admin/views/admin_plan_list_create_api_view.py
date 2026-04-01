from drf_yasg.utils import swagger_auto_schema
from rest_framework import status

from apps.main_admin.serializers import PlanCreateSerializer
from apps.billing.models import SubscriptionPlan
from apps.billing.services import invalidate_active_plans_cache

from .base import SuperAdminAPIView


class AdminPlanListCreateAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="List plans",
        operation_description="Return all subscription plans.",
        responses={200: "Plan list"},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.all().order_by("price")
        return self.success_response(
            data=[
                {
                    "id": plan.id,
                    "code": plan.code,
                    "name": plan.name,
                    "price": str(plan.price),
                    "duration_days": plan.duration_days,
                    "features": plan.features,
                    "is_active": plan.is_active,
                }
                for plan in plans
            ],
            message="Plans loaded.",
        )

    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Create plan",
        operation_description="Create a new subscription plan.",
        request_body=PlanCreateSerializer,
        responses={201: "Plan created", 400: "Validation error"},
    )
    def post(self, request):
        serializer = PlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        invalidate_active_plans_cache()
        return self.success_response(
            data={
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
                "price": str(plan.price),
                "duration_days": plan.duration_days,
                "features": plan.features,
                "is_active": plan.is_active,
            },
            message="Plan created successfully.",
            status_code=status.HTTP_201_CREATED,
        )
