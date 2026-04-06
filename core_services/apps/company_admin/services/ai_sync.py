import json
from datetime import timedelta
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest
import jwt
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.company.models import Company
from apps.company_admin.models import Driver, DriverAssignment, Product, Route, Shop, Vehicle


def _build_service_token(company_id: str) -> str:
    now = timezone.now()
    payload = {
        "token_type": "service",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.AI_INTERNAL_AUTH_TOKEN_TTL_SECONDS)).timestamp()),
        "iss": settings.AI_INTERNAL_AUTH_ISSUER,
        "aud": settings.AI_INTERNAL_AUTH_AUDIENCE,
        "service": "core_service",
        "sub": "core_service",
        "company_id": company_id,
        "permissions": ["ai.ingest", "ai.search", "ai.chat", "ai.doc.update", "ai.doc.delete"],
    }
    return jwt.encode(payload, settings.AI_INTERNAL_AUTH_SECRET, algorithm="HS256")


def _put_document(company_id: str, token: str, doc_id: str, text: str, metadata: dict[str, Any]) -> None:
    ai_url = f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/ai/documents/{doc_id}"
    body = json.dumps({"text": text, "metadata": metadata}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": str(company_id),
    }
    req = urlrequest.Request(ai_url, data=body, headers=headers, method="PUT")
    with urlrequest.urlopen(req, timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as response:
        response.read()


def build_company_knowledge_documents(company_id: str) -> list[dict[str, Any]]:
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return []

    shops = list(Shop.objects.filter(company_id=company_id).order_by("name").values("name", "owner_name", "location_display_name"))
    routes = list(Route.objects.filter(company_id=company_id).order_by("route_name").values("id", "route_name", "start_point", "end_point"))
    vehicles = list(Vehicle.objects.filter(company_id=company_id).order_by("name").values("name", "number_plate", "status", "fuel_percentage"))
    products = list(Product.objects.filter(company_id=company_id).order_by("name").values("name", "quantity_count", "rate", "shelf_life"))
    drivers = list(
        Driver.objects.filter(user__company_id=company_id)
        .order_by("name")
        .values("name", "status", "age", "user__email")
    )
    assignments = list(
        DriverAssignment.objects.filter(route__company_id=company_id)
        .order_by("-scheduled_at")[:100]
        .values("driver__name", "route__route_name", "vehicle__number_plate", "scheduled_at", "status", "notes")
    )

    route_shop_map: dict[str, list[str]] = {}
    if routes:
        route_ids = [item["id"] for item in routes]
        linked = (
            Route.objects.filter(id__in=route_ids)
            .prefetch_related("route_shops__shop")
            .all()
        )
        for route in linked:
            route_shop_map[str(route.id)] = [
                f"{entry.position}. {entry.shop.name}" for entry in route.route_shops.all()
            ]

    docs = [
        {
            "doc_id": f"company:{company_id}:profile",
            "text": (
                f"Company name: {company.name}. "
                f"Official email: {company.official_email or 'N/A'}. "
                f"Phone: {company.phone or 'N/A'}. "
                f"Address: {company.address or 'N/A'}. "
                f"Operational status: {company.operational_status}. "
                f"Total shops: {len(shops)}. Total routes: {len(routes)}. "
                f"Total drivers: {len(drivers)}. Total vehicles: {len(vehicles)}. "
                f"Total products: {len(products)}."
            ),
            "metadata": {"type": "company_profile", "company_id": str(company_id)},
        },
        {
            "doc_id": f"company:{company_id}:shops",
            "text": "Shops:\n" + "\n".join(
                [f"- {s['name']} (owner: {s['owner_name']}, location: {s['location_display_name'] or 'N/A'})" for s in shops]
            ),
            "metadata": {"type": "shops_snapshot", "company_id": str(company_id), "count": len(shops)},
        },
        {
            "doc_id": f"company:{company_id}:routes",
            "text": "Routes:\n" + "\n".join(
                [
                    f"- {r['route_name']} ({r['start_point']} -> {r['end_point']})"
                    + (f"; stops: {', '.join(route_shop_map.get(str(r['id']), []))}" if route_shop_map.get(str(r["id"])) else "")
                    for r in routes
                ]
            ),
            "metadata": {"type": "routes_snapshot", "company_id": str(company_id), "count": len(routes)},
        },
        {
            "doc_id": f"company:{company_id}:drivers",
            "text": "Drivers:\n" + "\n".join(
                [f"- {d['name']} (status: {d['status']}, age: {d['age']}, email: {d['user__email'] or 'N/A'})" for d in drivers]
            ),
            "metadata": {"type": "drivers_snapshot", "company_id": str(company_id), "count": len(drivers)},
        },
        {
            "doc_id": f"company:{company_id}:vehicles",
            "text": "Vehicles:\n" + "\n".join(
                [f"- {v['name']} ({v['number_plate']}), status: {v['status']}, fuel: {v['fuel_percentage']}%" for v in vehicles]
            ),
            "metadata": {"type": "vehicles_snapshot", "company_id": str(company_id), "count": len(vehicles)},
        },
        {
            "doc_id": f"company:{company_id}:products",
            "text": "Products:\n" + "\n".join(
                [f"- {p['name']}: quantity {p['quantity_count']}, rate {p['rate']}, shelf life {p['shelf_life'] or 'N/A'}" for p in products]
            ),
            "metadata": {"type": "products_snapshot", "company_id": str(company_id), "count": len(products)},
        },
        {
            "doc_id": f"company:{company_id}:assignments",
            "text": "Recent driver assignments:\n" + "\n".join(
                [
                    f"- driver {a['driver__name']} on route {a['route__route_name']} "
                    f"with vehicle {a['vehicle__number_plate']} at {a['scheduled_at']} "
                    f"(status: {a['status']}, notes: {a['notes'] or 'N/A'})"
                    for a in assignments
                ]
            ),
            "metadata": {"type": "assignments_snapshot", "company_id": str(company_id), "count": len(assignments)},
        },
    ]
    return docs


def sync_company_knowledge(company_id: str) -> dict[str, Any]:
    docs = build_company_knowledge_documents(company_id)
    if not docs:
        return {"company_id": str(company_id), "updated": 0, "skipped": True}

    token = _build_service_token(str(company_id))
    updated = 0
    for doc in docs:
        _put_document(
            company_id=str(company_id),
            token=token,
            doc_id=str(doc["doc_id"]),
            text=str(doc["text"] or ""),
            metadata=doc.get("metadata", {}) or {},
        )
        updated += 1
    return {"company_id": str(company_id), "updated": updated, "skipped": False}


def queue_company_ai_sync(company_id: str, reason: str = "model_change") -> bool:
    if not company_id:
        return False
    if not settings.AI_AUTOSYNC_ENABLED:
        return False
    cache_key = f"ai_sync:queued:{company_id}"
    queued = cache.add(cache_key, reason, timeout=max(15, settings.AI_SYNC_QUEUE_LOCK_SECONDS))
    return bool(queued)


def clear_company_ai_sync_lock(company_id: str) -> None:
    if company_id:
        cache.delete(f"ai_sync:queued:{company_id}")


def handle_ai_sync_exception(exc: Exception) -> RuntimeError:
    if isinstance(exc, urlerror.HTTPError):
        try:
            content = exc.read().decode("utf-8")
        except Exception:
            content = str(exc)
        return RuntimeError(f"AI sync HTTP error: {exc.code} {content}")
    return RuntimeError(f"AI sync failed: {exc}")
