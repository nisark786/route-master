import json
import logging
import time
from uuid import uuid4

from redis import Redis

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class PlanRegistry:
    def __init__(self) -> None:
        self._client = Redis.from_url(settings.celery_result_backend, decode_responses=True)
        self._memory_store: dict[str, tuple[float, str]] = {}

    def create(self, tenant_id: str, suggestions: list[dict], unmatched_route_ids: list[str]) -> str:
        plan_id = str(uuid4())
        key = self._key(plan_id)
        payload = {
            "tenant_id": tenant_id,
            "suggestions": suggestions,
            "unmatched_route_ids": unmatched_route_ids,
        }
        encoded = json.dumps(payload)
        ttl_seconds = settings.job_registry_ttl_seconds
        try:
            self._client.set(name=key, value=encoded, ex=ttl_seconds)
        except Exception:
            logger.exception("plan_registry_redis_write_failed key=%s fallback=memory", key)
            self._memory_store[key] = (time.time() + ttl_seconds, encoded)
        return plan_id

    def get(self, plan_id: str) -> dict | None:
        key = self._key(plan_id)
        raw: str | None = None
        try:
            raw = self._client.get(key)
        except Exception:
            logger.exception("plan_registry_redis_read_failed key=%s fallback=memory", key)

        if raw is None:
            memory_payload = self._memory_store.get(key)
            if memory_payload:
                expires_at, encoded = memory_payload
                if expires_at > time.time():
                    raw = encoded
                else:
                    self._memory_store.pop(key, None)

        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    @staticmethod
    def _key(plan_id: str) -> str:
        return f"ai_plan:{plan_id}"


plan_registry = PlanRegistry()
