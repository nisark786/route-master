from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.core.cache import cache
from rest_framework.exceptions import NotFound

from apps.main_admin.serializers import CompanyStatusUpdateSerializer
from apps.company.models import Company, CompanyActivityLog

from .base import SuperAdminAPIView


class AdminCompanyStatusUpdateAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Update company status",
        operation_description="Suspend or reactivate a company.",
        manual_parameters=[
            openapi.Parameter(
                "company_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        request_body=CompanyStatusUpdateSerializer,
        responses={200: "Company status updated", 400: "Validation error", 404: "Company not found"},
    )
    def post(self, request, company_id):
        serializer = CompanyStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        company = Company.objects.filter(id=company_id).first()
        if not company:
            raise NotFound("Company not found.")

        action = data["action"]
        reason = data["reason"]
        if action == "suspend":
            company.operational_status = Company.STATUS_SUSPENDED
            company.is_active = False
            company.suspension_reason = reason
        else:
            company.operational_status = Company.STATUS_ACTIVE
            company.is_active = True
            company.suspension_reason = ""
        company.save(update_fields=["operational_status", "is_active", "suspension_reason", "updated_at"])
        cache.delete(f"billing:company-subscription-state:{company.id}")

        CompanyActivityLog.objects.create(
            company=company,
            actor=request.user,
            action=f"COMPANY_{action.upper()}",
            details={"reason": reason},
        )
        return self.success_response(
            data={"operational_status": company.operational_status},
            message=f"Company {action}d successfully.",
        )
