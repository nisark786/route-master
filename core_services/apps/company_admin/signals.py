from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.company.models import Company
from apps.company_admin.models import Driver, DriverAssignment, Product, Route, RouteShop, Shop, Vehicle
from apps.company_admin.services.cache import invalidate_company_operational_caches
from apps.company_admin.services.ai_sync import queue_company_ai_sync
from apps.company_admin.tasks import sync_company_ai_knowledge_task


def _enqueue(company_id: str, reason: str) -> None:
    if not company_id:
        return
    if queue_company_ai_sync(str(company_id), reason=reason):
        sync_company_ai_knowledge_task.delay(str(company_id))


def _safe_field(instance, field_name):
    if field_name in instance.__dict__:
        return instance.__dict__.get(field_name)
    try:
        return getattr(instance, field_name)
    except Exception:
        return None


def _company_id_from_route(route_id):
    if not route_id:
        return None
    return Route.objects.filter(id=route_id).values_list("company_id", flat=True).first()


@receiver([post_save, post_delete], sender=Company)
def sync_on_company_change(sender, instance, **kwargs):
    invalidate_company_operational_caches(str(instance.id))
    _enqueue(str(instance.id), reason="company")


@receiver([post_save, post_delete], sender=Shop)
def sync_on_shop_change(sender, instance, **kwargs):
    company_id = _safe_field(instance, "company_id")
    invalidate_company_operational_caches(str(company_id) if company_id else "")
    _enqueue(str(company_id) if company_id else "", reason="shop")


@receiver([post_save, post_delete], sender=Route)
def sync_on_route_change(sender, instance, **kwargs):
    company_id = _safe_field(instance, "company_id")
    invalidate_company_operational_caches(str(company_id) if company_id else "")
    _enqueue(str(company_id) if company_id else "", reason="route")


@receiver([post_save, post_delete], sender=RouteShop)
def sync_on_route_shop_change(sender, instance, **kwargs):
    route_id = _safe_field(instance, "route_id")
    company_id = _company_id_from_route(route_id)
    invalidate_company_operational_caches(str(company_id) if company_id else "")
    _enqueue(str(company_id) if company_id else "", reason="route_shop")


@receiver([post_save, post_delete], sender=Vehicle)
def sync_on_vehicle_change(sender, instance, **kwargs):
    company_id = _safe_field(instance, "company_id")
    invalidate_company_operational_caches(str(company_id) if company_id else "")
    _enqueue(str(company_id) if company_id else "", reason="vehicle")


@receiver([post_save, post_delete], sender=Product)
def sync_on_product_change(sender, instance, **kwargs):
    company_id = _safe_field(instance, "company_id")
    invalidate_company_operational_caches(str(company_id) if company_id else "")
    _enqueue(str(company_id) if company_id else "", reason="product")


@receiver([post_save, post_delete], sender=Driver)
def sync_on_driver_change(sender, instance, **kwargs):
    company_id = getattr(instance.user, "company_id", None)
    invalidate_company_operational_caches(str(company_id) if company_id else "")
    _enqueue(str(company_id) if company_id else "", reason="driver")


@receiver([post_save, post_delete], sender=DriverAssignment)
def sync_on_assignment_change(sender, instance, **kwargs):
    route_id = _safe_field(instance, "route_id")
    company_id = _company_id_from_route(route_id)
    invalidate_company_operational_caches(str(company_id) if company_id else "")
    _enqueue(str(company_id) if company_id else "", reason="driver_assignment")
