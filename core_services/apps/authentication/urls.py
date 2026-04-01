from django.urls import path
from .views import (
    ChangeInitialPasswordAPIView,
    MobileLoginAPIView,
    LogoutAPIView,
    MeAPIView,
    RefreshTokenAPIView,
    WebLoginAPIView,
)

urlpatterns = [
    path("web/login/", WebLoginAPIView.as_view(), name="web-login"),
    path("mobile/login/", MobileLoginAPIView.as_view(), name="mobile-login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("refresh/", RefreshTokenAPIView.as_view(), name="refresh"),
    path('me/', MeAPIView.as_view()),
    path("change-initial-password/", ChangeInitialPasswordAPIView.as_view(), name="change-initial-password"),
]
