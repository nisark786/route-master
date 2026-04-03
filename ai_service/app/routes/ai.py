import logging
import time

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthContext
from app.celery_app import celery_app
from app.core.config import settings
from app.core.permissions import require_permissions
from app.core.tenancy import get_tenant_id
from app.schemas.ai import (
    AsyncIngestResponse,
    AsyncIngestStatusResponse,
    ChatRequest,
    ChatResponse,
    DispatchCopilotApproveRequest,
    DispatchCopilotApproveResponse,
    DispatchCopilotRequest,
    DispatchCopilotResponse,
    DocumentMutationResponse,
    DocumentUpdateRequest,
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.chunking import chunk_text
from app.services.job_registry import job_registry
from app.services.dispatch_copilot import dispatch_copilot_service
from app.services.qdrant_store import qdrant_store
from app.services.rag import rag_service
from app.tasks.ingest_tasks import ingest_documents_task

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
logger = logging.getLogger("uvicorn.error")


def _ingest_sync(payload: IngestRequest, tenant_id: str) -> int:
    total_points = 0
    for document in payload.documents:
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
    return total_points


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(
    payload: IngestRequest,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.ingest")),
):
    try:
        total_points = _ingest_sync(payload, tenant_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vector ingest failed: {exc}",
        ) from exc

    return IngestResponse(
        collection=settings.qdrant_collection,
        tenant_id=tenant_id,
        points_upserted=total_points,
    )


@router.post("/ingest/async", response_model=AsyncIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_documents_async(
    payload: IngestRequest,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.ingest")),
):
    task = ingest_documents_task.delay(payload.model_dump(), tenant_id)
    try:
        job_registry.register(task.id, tenant_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to register async job ownership: {exc}",
        ) from exc

    return AsyncIngestResponse(job_id=task.id, status="queued", tenant_id=tenant_id)


@router.get("/jobs/{job_id}", response_model=AsyncIngestStatusResponse)
async def get_async_ingest_job(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.ingest")),
):
    job_tenant_id = job_registry.get_tenant(job_id)
    if not job_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Job does not belong to tenant.")

    task = AsyncResult(job_id, app=celery_app)
    state = task.state.lower()
    points_upserted = 0
    error = None

    if task.successful():
        result = task.result if isinstance(task.result, dict) else {}
        points_upserted = int(result.get("points_upserted", 0))
        state = "succeeded"
    elif task.failed():
        state = "failed"
        error = str(task.result)
    elif state == "pending":
        state = "queued"

    return AsyncIngestStatusResponse(
        job_id=job_id,
        status=state,
        tenant_id=tenant_id,
        points_upserted=points_upserted,
        error=error,
    )


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    payload: SearchRequest,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.search")),
):
    try:
        scored_points = qdrant_store.search(
            tenant_id=tenant_id,
            query=payload.query,
            top_k=payload.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vector search failed: {exc}",
        ) from exc

    results: list[SearchResult] = []
    for point in scored_points:
        data = point.payload or {}
        results.append(
            SearchResult(
                score=float(point.score),
                doc_id=str(data.get("doc_id", "")),
                chunk_id=str(data.get("chunk_id", "")),
                text=str(data.get("text", "")),
                metadata=data.get("metadata", {}) or {},
            )
        )

    return SearchResponse(
        collection=settings.qdrant_collection,
        tenant_id=tenant_id,
        count=len(results),
        results=results,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    payload: ChatRequest,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.chat")),
):
    started_at = time.perf_counter()
    try:
        answer, sources = rag_service.answer(
            tenant_id=tenant_id,
            question=payload.query,
            top_k=payload.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"RAG generation failed: {exc}",
        ) from exc
    logger.info(
        "ai_chat_completed tenant=%s sources=%s total_ms=%.1f",
        tenant_id,
        len(sources),
        (time.perf_counter() - started_at) * 1000,
    )
    return ChatResponse(tenant_id=tenant_id, answer=answer, sources=sources)


@router.post("/dispatch-copilot", response_model=DispatchCopilotResponse)
async def dispatch_copilot(
    payload: DispatchCopilotRequest,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.dispatch")),
):
    try:
        return dispatch_copilot_service.suggest(tenant_id=tenant_id, payload=payload)
    except Exception as exc:
        logger.exception("dispatch_copilot_failed tenant=%s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Dispatch copilot failed: {exc}",
        ) from exc


@router.post("/dispatch-copilot/approve", response_model=DispatchCopilotApproveResponse)
async def approve_dispatch_copilot(
    payload: DispatchCopilotApproveRequest,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.dispatch")),
):
    try:
        return dispatch_copilot_service.approve(tenant_id=tenant_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("dispatch_copilot_approve_failed tenant=%s plan_id=%s", tenant_id, payload.plan_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Dispatch approval failed: {exc}",
        ) from exc


@router.put("/documents/{doc_id}", response_model=DocumentMutationResponse)
async def update_document(
    doc_id: str,
    payload: DocumentUpdateRequest,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.doc.update")),
):
    deleted = qdrant_store.delete_document(tenant_id=tenant_id, doc_id=doc_id)
    chunks = chunk_text(text=payload.text, size=settings.chunk_size, overlap=settings.chunk_overlap)
    inserted = qdrant_store.upsert_chunks(
        tenant_id=tenant_id,
        doc_id=doc_id,
        chunks=chunks,
        metadata=payload.metadata,
    )
    return DocumentMutationResponse(
        collection=settings.qdrant_collection,
        tenant_id=tenant_id,
        doc_id=doc_id,
        points_affected=deleted + inserted,
    )


@router.delete("/documents/{doc_id}", response_model=DocumentMutationResponse)
async def delete_document(
    doc_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth: AuthContext = Depends(require_permissions("ai.doc.delete")),
):
    deleted = qdrant_store.delete_document(tenant_id=tenant_id, doc_id=doc_id)
    return DocumentMutationResponse(
        collection=settings.qdrant_collection,
        tenant_id=tenant_id,
        doc_id=doc_id,
        points_affected=deleted,
    )
