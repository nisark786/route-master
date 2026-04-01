from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import LoginSerializer
from apps.authentication.services import (
    generate_tokens_for_user,
    get_login_identifier,
    increment_login_attempt,
    is_login_allowed,
    reset_login_attempts,
    validate_login_request,
)


class _BaseLoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    operation_description = (
        "Authenticate using email/password and issue an access token with "
        "client-specific refresh credentials."
    )

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Login user",
        operation_description=operation_description,
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(type=openapi.TYPE_STRING),
                        "role": openapi.Schema(type=openapi.TYPE_STRING),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                        "mobile_number": openapi.Schema(type=openapi.TYPE_STRING),
                        "company_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "must_change_password": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            400: "Validation error",
            429: "Too many attempts",
        },
    )
    def post(self, request):
        identifier = get_login_identifier(request.data)
        throttle_key = identifier.lower()
        if throttle_key and not is_login_allowed(throttle_key):
            return Response(
                {"message": "Too many failed login attempts. Please try again in 5 minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            user = validate_login_request(request.data)
        except serializers.ValidationError as exc:
            if throttle_key:
                increment_login_attempt(throttle_key)
            return self._build_error_response(exc.detail)

        if throttle_key:
            reset_login_attempts(throttle_key)
        tokens = generate_tokens_for_user(user)
        return self.build_success_response(user, tokens)

    def _build_error_response(self, errors):
        first_message = next(
            (
                str(value[0]) if isinstance(value, list) and value else str(value)
                for value in errors.values()
                if value
            ),
            "Login failed. Please check your credentials.",
        )
        return Response(
            {"message": first_message, "error": {"details": errors}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _build_response_payload(self, user, tokens):
        return {
            "message": "Login successful.",
            "access": tokens["access"],
            "role": user.role,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "company_id": user.company_id,
            "must_change_password": user.must_change_password,
        }

    def _set_refresh_cookie(self, response, refresh_token):
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite=settings.REFRESH_COOKIE_SAMESITE,
            domain=settings.REFRESH_COOKIE_DOMAIN,
        )

    def build_success_response(self, user, tokens):
        raise NotImplementedError


class WebLoginAPIView(_BaseLoginAPIView):
    operation_description = "Authenticate a web user and issue an access token with a refresh cookie."

    def build_success_response(self, user, tokens):
        response = Response(self._build_response_payload(user, tokens), status=status.HTTP_200_OK)
        self._set_refresh_cookie(response, tokens["refresh"])
        return response


class MobileLoginAPIView(_BaseLoginAPIView):
    operation_description = "Authenticate a mobile user and issue access and refresh tokens in the response body."

    def build_success_response(self, user, tokens):
        payload = self._build_response_payload(user, tokens)
        payload["refresh"] = tokens["refresh"]
        return Response(payload, status=status.HTTP_200_OK)
