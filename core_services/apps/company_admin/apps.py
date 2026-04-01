from django.apps import AppConfig


class CompanyAdminConfig(AppConfig):
    name = "apps.company_admin"

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
