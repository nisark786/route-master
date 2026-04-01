from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from apps.company_admin.services.ai_sync import queue_company_ai_sync
from apps.company_admin.tasks import sync_company_ai_knowledge_task

from .base import CompanyAdminAPIView


class AiSyncAPIView(CompanyAdminAPIView):
    required_permission = "ai.ingest"

    @swagger_auto_schema(
        tags=["Company Admin AI"],
        operation_summary="Trigger AI knowledge sync for current company",
        responses={
            202: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "queued": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "task_id": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        },
    )
    def post(self, request):
        company_id = str(request.user.company_id)
        if not queue_company_ai_sync(company_id, reason="manual"):
            return Response({"queued": False, "task_id": None}, status=status.HTTP_202_ACCEPTED)

        task = sync_company_ai_knowledge_task.delay(company_id)
        return Response({"queued": True, "task_id": task.id}, status=status.HTTP_202_ACCEPTED)
