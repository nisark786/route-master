from drf_yasg.utils import swagger_auto_schema

from apps.billing.models import PlanChangeLog

from .base import SuperAdminAPIView


class AdminPlanChangeLogAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Plan change logs",
        operation_description="Return recent plan upgrade/downgrade history.",
        responses={200: "Plan change logs"},
    )
    def get(self, request):
        logs = PlanChangeLog.objects.select_related("company", "old_plan", "new_plan", "changed_by")[:100]
        return self.success_response(
            data=[
                {
                    "id": log.id,
                    "company_name": log.company.name,
                    "old_plan": log.old_plan.name if log.old_plan else None,
                    "new_plan": log.new_plan.name if log.new_plan else None,
                    "changed_by": log.changed_by.email if log.changed_by else None,
                    "reason": log.reason,
                    "created_at": log.created_at,
                }
                for log in logs
            ],
            message="Plan change logs loaded.",
        )
