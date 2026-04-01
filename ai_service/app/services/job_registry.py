from redis import Redis

from app.core.config import settings


class JobRegistry:
    def __init__(self) -> None:
        self._client = Redis.from_url(settings.celery_result_backend, decode_responses=True)

    def register(self, job_id: str, tenant_id: str) -> None:
        key = f"ai_job:{job_id}:tenant"
        self._client.set(name=key, value=tenant_id, ex=settings.job_registry_ttl_seconds)

    def get_tenant(self, job_id: str) -> str | None:
        key = f"ai_job:{job_id}:tenant"
        value = self._client.get(key)
        return value if value else None


job_registry = JobRegistry()
