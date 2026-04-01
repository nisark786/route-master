from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import CompanySubscription, PaymentTransaction, PlanChangeLog
from apps.billing.serializers import RenewSubscriptionSerializer
from apps.billing.services import verify_razorpay_signature
from apps.company.models import Company, CompanyActivityLog


class CompleteSubscriptionRenewalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="Complete subscription renewal",
        operation_description="Verify renewal payment (if required), renew subscription, and reactivate company if suspended.",
        request_body=RenewSubscriptionSerializer,
        responses={
            200: openapi.Response(
                description="Subscription renewed",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "company_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "company_status": openapi.Schema(type=openapi.TYPE_STRING),
                        "subscription": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "plan_code": openapi.Schema(type=openapi.TYPE_STRING),
                                "plan_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "end_date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            },
                        ),
                    },
                ),
            ),
            400: "Payment validation error",
            403: "Only company admin can renew subscription",
            404: "Subscription not found",
        },
    )
    @transaction.atomic
    def post(self, request):
        if request.user.role != "COMPANY_ADMIN" or not request.user.company_id:
            return Response(
                {"message": "Only company admin can renew subscription."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RenewSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.context["plan"]
        data = serializer.validated_data

        subscription = CompanySubscription.objects.select_related("company", "plan").filter(
            company_id=request.user.company_id
        ).first()
        if not subscription:
            return Response({"message": "Company subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        if plan.price > 0:
            order_id = data.get("razorpay_order_id", "")
            payment_id = data.get("razorpay_payment_id", "")
            signature = data.get("razorpay_signature", "")
            if not all([order_id, payment_id, signature]):
                return Response({"message": "Payment details are required."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                verify_razorpay_signature(order_id, payment_id, signature)
            except Exception:
                return Response({"message": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            order_id = data.get("razorpay_order_id", "") or "TRIAL_RENEWAL"
            payment_id = data.get("razorpay_payment_id", "") or "TRIAL_RENEWAL"
            signature = data.get("razorpay_signature", "") or "TRIAL_RENEWAL"

        old_plan = subscription.plan
        now = timezone.now()
        current_end_date = subscription.end_date
        base_start = max(current_end_date, now)
        renewed_end_date = base_start + timedelta(days=plan.duration_days)
        queued_plan = bool(current_end_date > now and old_plan and old_plan.id != plan.id)
        effective_from = current_end_date if queued_plan else now

        if queued_plan:
            subscription.pending_plan = plan
            subscription.pending_plan_effective_at = current_end_date
        else:
            subscription.plan = plan
            subscription.pending_plan = None
            subscription.pending_plan_effective_at = None
        subscription.razorpay_order_id = order_id
        subscription.razorpay_payment_id = payment_id
        subscription.razorpay_signature = signature
        subscription.end_date = renewed_end_date
        subscription.amount_paid = plan.price
        subscription.currency = "INR"
        subscription.is_active = True
        subscription.save(
            update_fields=[
                "plan",
                "razorpay_order_id",
                "razorpay_payment_id",
                "razorpay_signature",
                "end_date",
                "amount_paid",
                "currency",
                "is_active",
                "pending_plan",
                "pending_plan_effective_at",
            ]
        )

        company = subscription.company
        reactivated = False
        if company.operational_status != Company.STATUS_ACTIVE or not company.is_active:
            company.operational_status = Company.STATUS_ACTIVE
            company.is_active = True
            company.suspension_reason = ""
            company.save(update_fields=["operational_status", "is_active", "suspension_reason", "updated_at"])
            reactivated = True

        invoice_number = f"INV-REN-{timezone.now().strftime('%Y%m%d')}-{str(company.id)[:8]}"
        PaymentTransaction.objects.create(
            company=company,
            subscription=subscription,
            provider="razorpay",
            order_id=order_id,
            payment_id=payment_id,
            invoice_number=invoice_number,
            amount=plan.price,
            currency="INR",
            status=PaymentTransaction.STATUS_SUCCESS,
            metadata={
                "plan_code": plan.code,
                "renewal": True,
                "queued_plan": queued_plan,
                "effective_from": effective_from.isoformat(),
            },
        )

        PlanChangeLog.objects.create(
            company=company,
            old_plan=old_plan,
            new_plan=plan,
            changed_by=request.user,
            reason="Subscription renewed.",
        )
        CompanyActivityLog.objects.create(
            company=company,
            actor=request.user,
            action="SUBSCRIPTION_RENEWED",
            details={
                "old_plan_code": old_plan.code if old_plan else None,
                "new_plan_code": plan.code,
                "renewed_end_date": renewed_end_date.isoformat(),
                "queued_plan": queued_plan,
                "effective_from": effective_from.isoformat(),
                "reactivated": reactivated,
            },
        )

        cache.delete(f"billing:company-subscription-state:{company.id}")
        cache.delete(f"company_profile:{company.id}")
        cache.delete(f"user_profile:{request.user.id}")

        return Response(
            {
                "message": (
                    "Subscription renewed successfully. New plan is queued and will activate at current expiry."
                    if queued_plan
                    else "Subscription renewed successfully."
                ),
                "company_id": str(company.id),
                "company_status": company.operational_status,
                "subscription": {
                    "plan_code": subscription.plan.code if subscription.plan else None,
                    "plan_name": subscription.plan.name if subscription.plan else None,
                    "end_date": renewed_end_date,
                    "is_active": subscription.is_active,
                    "queued_plan_code": plan.code if queued_plan else None,
                    "queued_plan_name": plan.name if queued_plan else None,
                    "queued_plan_effective_at": effective_from if queued_plan else None,
                },
            },
            status=status.HTTP_200_OK,
        )
