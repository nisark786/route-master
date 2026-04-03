import logging
import time

from redis import Redis

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class JobRegistry:
    def __init__(self) -> None:
        self._client = Redis.from_url(settings.celery_result_backend, decode_responses=True)
        self._memory_store: dict[str, tuple[float, str]] = {}

    def register(self, job_id: str, tenant_id: str) -> None:
        key = f"ai_job:{job_id}:tenant"
        ttl_seconds = settings.job_registry_ttl_seconds
        try:
            self._client.set(name=key, value=tenant_id, ex=ttl_seconds)
        except Exception:
            logger.exception("job_registry_redis_write_failed key=%s fallback=memory", key)
            self._memory_store[key] = (time.time() + ttl_seconds, tenant_id)

    def get_tenant(self, job_id: str) -> str | None:
        key = f"ai_job:{job_id}:tenant"
        value: str | None = None
        try:
            value = self._client.get(key)
        except Exception:
            logger.exception("job_registry_redis_read_failed key=%s fallback=memory", key)

        if value is None:
            memory_payload = self._memory_store.get(key)
            if memory_payload:
                expires_at, stored_tenant = memory_payload
                if expires_at > time.time():
                    value = stored_tenant
                else:
                    self._memory_store.pop(key, None)
        return value if value else None


job_registry = JobRegistry()
