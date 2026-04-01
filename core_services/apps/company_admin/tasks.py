from celery import shared_task

from apps.company.models import Company
from apps.company_admin.services.ai_sync import (
    clear_company_ai_sync_lock,
    handle_ai_sync_exception,
    queue_company_ai_sync,
    sync_company_knowledge,
)


@shared_task(bind=True, name="company_admin.sync_company_ai_knowledge")
def sync_company_ai_knowledge_task(self, company_id: str):
    try:
        return sync_company_knowledge(company_id)
    except Exception as exc:
        raise handle_ai_sync_exception(exc) from exc
    finally:
        clear_company_ai_sync_lock(company_id)


@shared_task(bind=True, name="company_admin.sync_all_companies_ai_knowledge")
def sync_all_companies_ai_knowledge_task(self):
    company_ids = list(Company.objects.values_list("id", flat=True))
    queued = 0
    for company_id in company_ids:
        company_id_str = str(company_id)
        if queue_company_ai_sync(company_id_str, reason="scheduled_full_sync"):
            sync_company_ai_knowledge_task.delay(company_id_str)
            queued += 1
    return {
        "companies_total": len(company_ids),
        "companies_queued": queued,
    }
