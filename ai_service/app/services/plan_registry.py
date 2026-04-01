import json
from uuid import uuid4

from redis import Redis

from app.core.config import settings


class PlanRegistry:
    def __init__(self) -> None:
        self._client = Redis.from_url(settings.celery_result_backend, decode_responses=True)

    def create(self, tenant_id: str, suggestions: list[dict], unmatched_route_ids: list[str]) -> str:
        plan_id = str(uuid4())
        key = self._key(plan_id)
        payload = {
            "tenant_id": tenant_id,
            "suggestions": suggestions,
            "unmatched_route_ids": unmatched_route_ids,
        }
        self._client.set(name=key, value=json.dumps(payload), ex=settings.job_registry_ttl_seconds)
        return plan_id

    def get(self, plan_id: str) -> dict | None:
        raw = self._client.get(self._key(plan_id))
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
