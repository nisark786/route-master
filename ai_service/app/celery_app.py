from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "ai_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ingest_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    enable_utc=True,
    task_track_started=True,
    result_expires=settings.celery_result_expires_seconds,
)
