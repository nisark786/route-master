from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import MeSerializer
from apps.authentication.services import get_user_cache


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Current user profile",
        operation_description="Return authenticated user details.",
        responses={200: MeSerializer, 401: "Unauthorized"},
    )
    def get(self, request):
        data = get_user_cache(request.user)
        return Response(data, status=status.HTTP_200_OK)
