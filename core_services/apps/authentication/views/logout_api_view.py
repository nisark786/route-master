from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.services import invalidate_user_cache


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Logout user",
        operation_description="Blacklist refresh token from cookie and clear cookie.",
        responses={
            200: openapi.Response(
                description="Logout successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            400: "Invalid token",
            401: "Unauthorized",
        },
    )
    def post(self, request):
        try:
            refresh_token = (
                request.data.get("refresh")
                or request.COOKIES.get("refresh_token")
                or ""
            )
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            response = Response(
                {"message": "Logout successful.", "detail": "Logout successful."},
                status=status.HTTP_200_OK,
            )
            response.delete_cookie("refresh_token")
            invalidate_user_cache(request.user.id)
            return response
        except Exception:
            return Response({"message": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
