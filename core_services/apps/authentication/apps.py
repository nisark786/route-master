from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    name = 'apps.authentication'

    def ready(self):
        try:
            from apps.authentication.rbac import ensure_system_rbac_baseline

            ensure_system_rbac_baseline()
        except Exception:
            pass
