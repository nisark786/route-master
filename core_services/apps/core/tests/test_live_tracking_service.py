from datetime import datetime, timezone
from decimal import Decimal

from apps.core.services.live_tracking import LiveTrackingService, _safe_float


class _FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, ex=None):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


class _FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, field, direction):
        reverse = direction == -1
        self.items.sort(key=lambda item: item.get(field), reverse=reverse)
        return self

    def limit(self, limit):
        self.items = self.items[:limit]
        return self

    def __iter__(self):
        return iter(self.items)


class _FakeCollection:
    def __init__(self):
        self.indexes = []
        self.items = []

    def create_index(self, fields, name=None):
        self.indexes.append((fields, name))

    def insert_one(self, payload):
        self.items.append(payload)

    def find(self, query, projection):
        results = [
            item
            for item in self.items
            if item["company_id"] == query["company_id"]
            and item["assignment_id"] == query["assignment_id"]
        ]
        return _FakeCursor(results)


class _FakeDatabase:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, name):
        return self.collection


class _FakeMongoClient:
    def __init__(self, collection):
        self.database = _FakeDatabase(collection)

    def __getitem__(self, name):
        return self.database


class _FakeChannelLayer:
    def __init__(self):
        self.sent = []

    def group_send(self, group, payload):
        self.sent.append((group, payload))


def test_safe_float_handles_decimals_and_invalid_values():
    assert _safe_float(Decimal("10.5")) == 10.5
    assert _safe_float("7.2") == 7.2
    assert _safe_float("bad", default=3.0) == 3.0


def test_live_tracking_service_update_and_history(monkeypatch):
    collection = _FakeCollection()
    channel_layer = _FakeChannelLayer()

    monkeypatch.setattr("apps.core.services.live_tracking.Redis.from_url", lambda *args, **kwargs: _FakeRedis())
    monkeypatch.setattr("apps.core.services.live_tracking.MongoClient", lambda *args, **kwargs: _FakeMongoClient(collection))
    monkeypatch.setattr("apps.core.services.live_tracking.get_channel_layer", lambda: channel_layer)
    monkeypatch.setattr("apps.core.services.live_tracking.async_to_sync", lambda func: func)

    service = LiveTrackingService()
    payload = service.update_location(
        company_id="company-1",
        assignment_id="assignment-1",
        route_run_id="run-1",
        vehicle_id="vehicle-1",
        driver_id="driver-1",
        latitude=12.9,
        longitude=77.5,
        speed_kph=Decimal("22.4"),
        heading=180,
        captured_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    )

    latest = service.get_latest_for_assignment("company-1", "assignment-1")
    history = service.get_history_for_assignment("company-1", "assignment-1")

    assert payload["speed_kph"] == 22.4
    assert latest["route_run_id"] == "run-1"
    assert len(history) == 1
    assert channel_layer.sent[0][0] == "live_tracking_company_company-1"


def test_live_tracking_service_publish_stop_update(monkeypatch):
    collection = _FakeCollection()
    channel_layer = _FakeChannelLayer()

    monkeypatch.setattr("apps.core.services.live_tracking.Redis.from_url", lambda *args, **kwargs: _FakeRedis())
    monkeypatch.setattr("apps.core.services.live_tracking.MongoClient", lambda *args, **kwargs: _FakeMongoClient(collection))
    monkeypatch.setattr("apps.core.services.live_tracking.get_channel_layer", lambda: channel_layer)
    monkeypatch.setattr("apps.core.services.live_tracking.async_to_sync", lambda func: func)

    service = LiveTrackingService()
    service.publish_stop_update(
        company_id="company-1",
        assignment_id="assignment-1",
        route_run_id="run-1",
        stop_id="stop-1",
        shop_id="shop-1",
        status="COMPLETED",
    )

    assert channel_layer.sent[0][1]["payload"]["event"] == "stop_update"
