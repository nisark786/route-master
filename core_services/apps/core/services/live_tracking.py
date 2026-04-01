import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from pymongo import ASCENDING, DESCENDING, MongoClient
from redis import Redis


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class LiveTrackingService:
    def __init__(self):
        self._redis = None
        self._mongo = None
        self._db = None
        self._collection = None
        self._indexes_ensured = False

    def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _get_collection(self):
        if self._collection is None:
            self._mongo = MongoClient(settings.MONGO_URI, tz_aware=True)
            self._db = self._mongo[settings.MONGO_DB_NAME]
            self._collection = self._db[settings.MONGO_LOCATIONS_COLLECTION]
        self._ensure_indexes()
        return self._collection

    def _ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        collection = self._collection
        if collection is None:
            return
        collection.create_index(
            [
                ("company_id", ASCENDING),
                ("assignment_id", ASCENDING),
                ("received_at", DESCENDING),
            ],
            name="idx_company_assignment_received",
        )
        collection.create_index(
            [
                ("vehicle_id", ASCENDING),
                ("received_at", DESCENDING),
            ],
            name="idx_vehicle_received",
        )
        self._indexes_ensured = True

    @staticmethod
    def _latest_key(company_id: str, assignment_id: str) -> str:
        return f"live_tracking:company:{company_id}:assignment:{assignment_id}:latest"

    def update_location(
        self,
        *,
        company_id: str,
        assignment_id: str,
        route_run_id: str,
        vehicle_id: str,
        driver_id: str,
        latitude: float,
        longitude: float,
        speed_kph: float,
        heading: float,
        captured_at: datetime | None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        payload = {
            "company_id": str(company_id),
            "assignment_id": str(assignment_id),
            "route_run_id": str(route_run_id),
            "vehicle_id": str(vehicle_id),
            "driver_id": str(driver_id),
            "latitude": _safe_float(latitude),
            "longitude": _safe_float(longitude),
            "speed_kph": _safe_float(speed_kph),
            "heading": _safe_float(heading),
            "captured_at": (captured_at or now).isoformat(),
            "received_at": now.isoformat(),
        }

        collection = self._get_collection()
        collection.insert_one(payload.copy())

        latest_key = self._latest_key(str(company_id), str(assignment_id))
        self._get_redis().set(
            latest_key,
            json.dumps(payload),
            ex=settings.LIVE_TRACK_LATEST_TTL_SECONDS,
        )

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"live_tracking_company_{company_id}",
                {
                    "type": "live_location_update",
                    "payload": {
                        "event": "location_update",
                        **payload,
                    },
                },
            )

        return payload

    def publish_stop_update(
        self,
        *,
        company_id: str,
        assignment_id: str,
        route_run_id: str,
        stop_id: str,
        shop_id: str,
        status: str,
        check_in_at: datetime | None = None,
        check_out_at: datetime | None = None,
        skipped_at: datetime | None = None,
        skip_reason: str | None = None,
    ) -> None:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        payload = {
            "event": "stop_update",
            "company_id": str(company_id),
            "assignment_id": str(assignment_id),
            "route_run_id": str(route_run_id),
            "stop_id": str(stop_id),
            "shop_id": str(shop_id),
            "status": status,
            "check_in_at": check_in_at.isoformat() if check_in_at else None,
            "check_out_at": check_out_at.isoformat() if check_out_at else None,
            "skipped_at": skipped_at.isoformat() if skipped_at else None,
            "skip_reason": skip_reason or "",
        }
        async_to_sync(channel_layer.group_send)(
            f"live_tracking_company_{company_id}",
            {
                "type": "live_location_update",
                "payload": payload,
            },
        )

    def get_latest_for_assignment(self, company_id: str, assignment_id: str) -> dict[str, Any] | None:
        raw = self._get_redis().get(self._latest_key(str(company_id), str(assignment_id)))
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def get_latest_for_assignments(self, company_id: str, assignment_ids: list[str]) -> dict[str, dict[str, Any] | None]:
        normalized_ids = [str(assignment_id) for assignment_id in assignment_ids if assignment_id]
        if not normalized_ids:
            return {}

        redis_client = self._get_redis()
        keys = [self._latest_key(str(company_id), assignment_id) for assignment_id in normalized_ids]
        raw_values = redis_client.mget(keys)

        latest_map: dict[str, dict[str, Any] | None] = {}
        for assignment_id, raw in zip(normalized_ids, raw_values):
            if not raw:
                latest_map[assignment_id] = None
                continue
            try:
                latest_map[assignment_id] = json.loads(raw)
            except Exception:
                latest_map[assignment_id] = None
        return latest_map

    def get_history_for_assignment(self, company_id: str, assignment_id: str, limit: int = 500) -> list[dict[str, Any]]:
        collection = self._get_collection()
        capped_limit = max(1, min(int(limit), 2000))
        cursor = (
            collection.find(
                {"company_id": str(company_id), "assignment_id": str(assignment_id)},
                {
                    "_id": 0,
                    "assignment_id": 1,
                    "vehicle_id": 1,
                    "driver_id": 1,
                    "latitude": 1,
                    "longitude": 1,
                    "speed_kph": 1,
                    "heading": 1,
                    "captured_at": 1,
                    "received_at": 1,
                },
            )
            .sort("received_at", ASCENDING)
            .limit(capped_limit)
        )
        return [item for item in cursor]


live_tracking_service = LiveTrackingService()
