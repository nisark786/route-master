from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class RefreshTokenAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Refresh access token",
        operation_description="Issue a new access token using refresh token from HttpOnly cookie.",
        responses={
            200: openapi.Response(
                description="Access token generated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"access": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            400: "Refresh token missing",
            401: "Invalid or expired refresh token",
        },
    )
    def post(self, request):
        refresh_token = (
            request.data.get("refresh")
            or request.COOKIES.get("refresh_token")
            or ""
        )
        if not refresh_token:
            return Response({"message": "Refresh token missing."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({"message": "Token refreshed successfully.", "access": access_token}, status=status.HTTP_200_OK)
        except TokenError:
            return Response(
                {"message": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
