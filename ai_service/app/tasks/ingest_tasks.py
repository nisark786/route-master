from app.core.config import settings
from app.schemas.ai import IngestRequest
from app.services.chunking import chunk_text
from app.services.qdrant_store import qdrant_store
from app.celery_app import celery_app


@celery_app.task(name="ai.tasks.ingest_documents")
def ingest_documents_task(payload: dict, tenant_id: str) -> dict:
    request = IngestRequest.model_validate(payload)
    total_points = 0

    for document in request.documents:
        chunks = chunk_text(
            text=document.text,
            size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        total_points += qdrant_store.upsert_chunks(
            tenant_id=tenant_id,
            doc_id=document.doc_id,
            chunks=chunks,
            metadata=document.metadata,
        )

    return {
        "collection": settings.qdrant_collection,
        "tenant_id": tenant_id,
        "points_upserted": total_points,
    }
