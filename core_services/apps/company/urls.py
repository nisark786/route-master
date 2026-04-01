from django.urls import path

from .views import CompanyProfileAPIView

urlpatterns = [
    path("profile/", CompanyProfileAPIView.as_view(), name="company-profile"),
]
