try:
    from .celery import app as celery_app
except Exception:  # Celery is optional in local setups until installed.
    celery_app = None

__all__ = ("celery_app",)
