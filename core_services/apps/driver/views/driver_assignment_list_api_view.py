from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema

from apps.company_admin.models import DriverAssignment
from apps.driver.serializers import DriverAssignmentListItemSerializer
from apps.driver.views.helpers import get_driver_for_user

from .base import DriverAPIView


class DriverAssignmentListAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="List assigned routes for logged in driver",
        responses={200: "Assigned routes loaded"},
    )
    def get(self, request):
        driver = get_driver_for_user(request.user)
        assignments = (
            DriverAssignment.objects.filter(
                driver_id=driver.id,
            )
            .filter(Q(status=DriverAssignment.STATUS_ASSIGNED) | Q(status=DriverAssignment.STATUS_IN_ROUTE))
            .select_related("route", "vehicle")
            .prefetch_related("route__route_shops")
            .order_by("-scheduled_at", "-created_at")
        )
        data = DriverAssignmentListItemSerializer(assignments, many=True).data
        return self.success_response(data=data, message="Assigned routes loaded.")
