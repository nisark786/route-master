from django.urls import path

from apps.driver.views import (
    DriverAssignmentInventoryAPIView,
    DriverAssignmentDetailAPIView,
    DriverAssignmentListAPIView,
    DriverLocationUpdateAPIView,
    DriverAssignmentStartAPIView,
    DriverStopCheckInAPIView,
    DriverStopCheckOutAPIView,
    DriverStopCompleteOrderAPIView,
    DriverStopDetailAPIView,
    DriverStopSkipAPIView,
)

urlpatterns = [
    path("assignments/", DriverAssignmentListAPIView.as_view(), name="driver-assignment-list"),
    path(
        "assignments/<uuid:assignment_id>/inventory/",
        DriverAssignmentInventoryAPIView.as_view(),
        name="driver-assignment-inventory",
    ),
    path("assignments/<uuid:assignment_id>/start/", DriverAssignmentStartAPIView.as_view(), name="driver-assignment-start"),
    path("assignments/<uuid:assignment_id>/location/", DriverLocationUpdateAPIView.as_view(), name="driver-assignment-location-update"),
    path("assignments/<uuid:assignment_id>/", DriverAssignmentDetailAPIView.as_view(), name="driver-assignment-detail"),
    path("assignments/<uuid:assignment_id>/shops/<uuid:shop_id>/", DriverStopDetailAPIView.as_view(), name="driver-stop-detail"),
    path(
        "assignments/<uuid:assignment_id>/shops/<uuid:shop_id>/check-in/",
        DriverStopCheckInAPIView.as_view(),
        name="driver-stop-check-in",
    ),
    path(
        "assignments/<uuid:assignment_id>/shops/<uuid:shop_id>/skip/",
        DriverStopSkipAPIView.as_view(),
        name="driver-stop-skip",
    ),
    path(
        "assignments/<uuid:assignment_id>/shops/<uuid:shop_id>/complete-order/",
        DriverStopCompleteOrderAPIView.as_view(),
        name="driver-stop-complete-order",
    ),
    path(
        "assignments/<uuid:assignment_id>/shops/<uuid:shop_id>/check-out/",
        DriverStopCheckOutAPIView.as_view(),
        name="driver-stop-check-out",
    ),
]
