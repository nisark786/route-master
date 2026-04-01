from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Route Management API",
        default_version="v1",
        description="API documentation for Route Management SaaS",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("django_prometheus.urls")),
    path("", include("apps.core.urls_health")),

    path('api/auth/', include('apps.authentication.urls')),
    path('api/billing/', include('apps.billing.urls')),
    path('api/company/', include('apps.company.urls')),
    path('api/company-admin/', include('apps.company_admin.urls')),
    path('api/admin/', include('apps.main_admin.urls')),
    path('api/driver/', include('apps.driver.urls')),
    path('api/shop-owner/', include('apps.shops.urls')),
    path('api/chat/', include('apps.chats.urls')),


     path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

