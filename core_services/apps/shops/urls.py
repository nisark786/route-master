from django.urls import path

from apps.shops.views import (
    ShopOwnerDashboardAPIView,
    ShopOwnerDeliveryDetailAPIView,
    ShopOwnerDeliveryListAPIView,
)

urlpatterns = [
    path("dashboard/", ShopOwnerDashboardAPIView.as_view(), name="shop-owner-dashboard"),
    path("deliveries/", ShopOwnerDeliveryListAPIView.as_view(), name="shop-owner-delivery-list"),
    path("deliveries/<uuid:stop_id>/", ShopOwnerDeliveryDetailAPIView.as_view(), name="shop-owner-delivery-detail"),
]
