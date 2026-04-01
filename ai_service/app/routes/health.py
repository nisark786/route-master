from fastapi import APIRouter

from app.services.qdrant_store import qdrant_store

router = APIRouter()


@router.get("/health")
async def health_check():
    qdrant_ok = True
    try:
        qdrant_store.client.get_collections()
    except Exception:
        qdrant_ok = False
    return {"status": "ok", "qdrant": "up" if qdrant_ok else "down"}
