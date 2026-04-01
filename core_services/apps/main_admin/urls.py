from django.urls import path

from apps.main_admin.views import (
    AdminAnalyticsAPIView,
    AdminCompanyDetailAPIView,
    AdminCompanyListAPIView,
    AdminCompanyStatusUpdateAPIView,
    AdminMonitoringAPIView,
    AdminOverviewAPIView,
    AdminPaymentListAPIView,
    AdminPlanChangeLogAPIView,
    AdminPlanListCreateAPIView,
    AdminPlanUpdateAPIView,
)

urlpatterns = [
    path("overview/", AdminOverviewAPIView.as_view(), name="admin-overview"),
    path("analytics/", AdminAnalyticsAPIView.as_view(), name="admin-analytics"),
    path("companies/", AdminCompanyListAPIView.as_view(), name="admin-companies"),
    path("companies/<uuid:company_id>/", AdminCompanyDetailAPIView.as_view(), name="admin-company-detail"),
    path(
        "companies/<uuid:company_id>/status/",
        AdminCompanyStatusUpdateAPIView.as_view(),
        name="admin-company-status-update",
    ),
    path("plans/", AdminPlanListCreateAPIView.as_view(), name="admin-plan-list-create"),
    path("plans/<int:plan_id>/", AdminPlanUpdateAPIView.as_view(), name="admin-plan-update"),
    path("plan-change-logs/", AdminPlanChangeLogAPIView.as_view(), name="admin-plan-change-logs"),
    path("payments/", AdminPaymentListAPIView.as_view(), name="admin-payments"),
    path("monitoring/", AdminMonitoringAPIView.as_view(), name="admin-monitoring"),
]
