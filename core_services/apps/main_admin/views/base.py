from decimal import Decimal

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from apps.core.permissions import HasPermissionCode


def safe_decimal(value):
    return value or Decimal("0")


class SuperAdminAPIView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = "main_admin.access"

    def success_response(self, data=None, message="Request completed successfully.", status_code=status.HTTP_200_OK, meta=None):
        payload = {
            "success": True,
            "message": message,
            "data": data,
        }
        if meta is not None:
            payload["meta"] = meta
        return Response(payload, status=status_code)

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response is None:
            return response

        detail = response.data
        message = "Request failed."
        if isinstance(detail, dict):
            message = detail.get("detail") or detail.get("error") or detail.get("message") or message
            if message == "Request failed.":
                for value in detail.values():
                    if isinstance(value, list) and value:
                        message = str(value[0])
                        break
                    if isinstance(value, str) and value.strip():
                        message = value
                        break
        elif isinstance(detail, list):
            message = str(detail[0]) if detail else "Validation failed."
        elif detail:
            message = str(detail)

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "VALIDATION_ERROR"
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "UNAUTHORIZED"
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "FORBIDDEN"
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "NOT_FOUND"
        else:
            error_code = "REQUEST_ERROR"

        response.data = {
            "success": False,
            "message": message,
            "error": {
                "code": error_code,
                "details": detail,
            },
        }
        return response

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
