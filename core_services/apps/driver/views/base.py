from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasPermissionCode


class DriverAPIView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = "driver.access"

    def success_response(self, data=None, message="Request completed successfully.", status_code=status.HTTP_200_OK):
        return Response({"success": True, "message": message, "data": data}, status=status_code)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.company_id:
            raise PermissionDenied("Driver is not linked to a company.")
