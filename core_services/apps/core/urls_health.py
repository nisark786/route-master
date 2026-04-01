from django.urls import path

from .views_health import HealthCheckView


urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
]
