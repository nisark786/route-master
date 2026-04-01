from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound

from apps.main_admin.serializers import PlanUpdateSerializer
from apps.billing.models import SubscriptionPlan
from apps.billing.services import invalidate_active_plans_cache

from .base import SuperAdminAPIView


class AdminPlanUpdateAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Update plan",
        operation_description="Partially update an existing subscription plan.",
        manual_parameters=[
            openapi.Parameter("plan_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True)
        ],
        request_body=PlanUpdateSerializer,
        responses={200: "Plan updated", 400: "Validation error", 404: "Plan not found"},
    )
    def patch(self, request, plan_id):
        plan = SubscriptionPlan.objects.filter(id=plan_id).first()
        if not plan:
            raise NotFound("Plan not found.")

        serializer = PlanUpdateSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_plan = serializer.save()
        invalidate_active_plans_cache()

        return self.success_response(
            data={
                "id": updated_plan.id,
                "code": updated_plan.code,
                "name": updated_plan.name,
                "price": str(updated_plan.price),
                "duration_days": updated_plan.duration_days,
                "features": updated_plan.features,
                "is_active": updated_plan.is_active,
            },
            message="Plan updated successfully.",
        )
