from django.core.cache import cache
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.company.serializers import CompanyProfileSerializer, CompanyProfileUpdateSerializer
from apps.company_admin.services.cache import company_profile_cache_key


class CompanyProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Company"],
        operation_summary="Get company profile",
        operation_description="Return current authenticated user's company profile with subscription info.",
        responses={200: CompanyProfileSerializer, 401: "Unauthorized", 404: "Company profile not found"},
    )
    def get(self, request):
        company = request.user.company
        if not company:
            return Response({"error": "Company profile not found."}, status=status.HTTP_404_NOT_FOUND)

        cache_key = company_profile_cache_key(company.id)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        company = (
            company.__class__.objects.select_related(
                "companysubscription__plan",
                "companysubscription__pending_plan",
            )
            .filter(id=company.id)
            .first()
        )
        serializer = CompanyProfileSerializer(company)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company"],
        operation_summary="Update company profile",
        operation_description="Update authenticated company admin profile fields.",
        request_body=CompanyProfileUpdateSerializer,
        responses={200: CompanyProfileSerializer, 400: "Validation error", 401: "Unauthorized", 403: "Forbidden"},
    )
    def patch(self, request):
        if request.user.role != "COMPANY_ADMIN":
            raise PermissionDenied("Only company admin can update company profile.")

        company = request.user.company
        if not company:
            return Response({"error": "Company profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CompanyProfileUpdateSerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        cache_key = company_profile_cache_key(company.id)
        cache.delete(cache_key)
        fresh = CompanyProfileSerializer(
            company.__class__.objects.select_related(
                "companysubscription__plan",
                "companysubscription__pending_plan",
            ).get(id=company.id)
        ).data
        cache.set(cache_key, fresh, timeout=300)
        return Response(fresh, status=status.HTTP_200_OK)
