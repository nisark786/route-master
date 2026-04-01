from django.urls import path

from .views import (
    CompleteCompanyRegistrationAPIView,
    CompleteSubscriptionRenewalAPIView,
    CompanyBillingTransactionListAPIView,
    CreateRegistrationOrderAPIView,
    CreateSubscriptionRenewalOrderAPIView,
    ResendCompanyRegistrationOtpAPIView,
    StartCompanyRegistrationAPIView,
    SubscriptionPlanListAPIView,
    VerifyCompanyRegistrationOtpAPIView,
)

urlpatterns = [
    path("plans/", SubscriptionPlanListAPIView.as_view(), name="subscription-plans"),
    path("registrations/start/", StartCompanyRegistrationAPIView.as_view(), name="registration-start"),
    path("registrations/verify-otp/", VerifyCompanyRegistrationOtpAPIView.as_view(), name="registration-verify-otp"),
    path("registrations/resend-otp/", ResendCompanyRegistrationOtpAPIView.as_view(), name="registration-resend-otp"),
    path("registrations/create-order/", CreateRegistrationOrderAPIView.as_view(), name="registration-create-order"),
    path("registrations/complete/", CompleteCompanyRegistrationAPIView.as_view(), name="registration-complete"),
    path("subscriptions/transactions/", CompanyBillingTransactionListAPIView.as_view(), name="subscription-transactions"),
    path("subscriptions/renew/create-order/", CreateSubscriptionRenewalOrderAPIView.as_view(), name="subscription-renew-create-order"),
    path("subscriptions/renew/complete/", CompleteSubscriptionRenewalAPIView.as_view(), name="subscription-renew-complete"),
]
