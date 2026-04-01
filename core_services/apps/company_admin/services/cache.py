from django.core.cache import cache


def _company_scope_version_key(company_id):
    return f"company_scope_version:{company_id}"


def get_company_scope_cache_version(company_id):
    if not company_id:
        return 1
    key = _company_scope_version_key(company_id)
    current = cache.get(key)
    if current is None:
        current = 1
        cache.set(key, current, timeout=60 * 60 * 24 * 30)
    return int(current)


def bump_company_scope_cache_version(company_id):
    if not company_id:
        return
    key = _company_scope_version_key(company_id)
    current = get_company_scope_cache_version(company_id)
    cache.set(key, current + 1, timeout=60 * 60 * 24 * 30)


def company_dashboard_cache_key(company_id):
    version = get_company_scope_cache_version(company_id)
    return f"company-admin-dashboard-overview:{company_id}:v{version}"


def company_profile_cache_key(company_id):
    version = get_company_scope_cache_version(company_id)
    return f"company_profile:{company_id}:v{version}"


def company_collection_cache_key(company_id, resource, *parts):
    version = get_company_scope_cache_version(company_id)
    suffix = ":".join(str(part) for part in parts if part is not None and str(part) != "")
    base = f"company_collection:{resource}:{company_id}:v{version}"
    return f"{base}:{suffix}" if suffix else base


def invalidate_company_operational_caches(company_id):
    if not company_id:
        return
    bump_company_scope_cache_version(company_id)
