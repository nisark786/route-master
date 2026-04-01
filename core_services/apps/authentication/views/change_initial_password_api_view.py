from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import ChangeInitialPasswordSerializer
from apps.authentication.services import invalidate_user_cache


class ChangeInitialPasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Change initial password",
        operation_description="Set a new password after first login using temporary credentials.",
        request_body=ChangeInitialPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Password changed",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            400: "Validation error",
            401: "Unauthorized",
        },
    )
    def post(self, request):
        serializer = ChangeInitialPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.must_change_password = False
        request.user.save(update_fields=["password", "must_change_password"])
        invalidate_user_cache(request.user.id)

        return Response(
            {"message": "Password updated successfully.", "detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )
