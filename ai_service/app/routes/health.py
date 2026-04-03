import asyncio

from fastapi import APIRouter

from app.services.qdrant_store import qdrant_store

router = APIRouter()


@router.get("/healthz")
async def healthz_check():
    return {"status": "ok"}


@router.get("/health")
async def health_check():
    qdrant_ok = True
    try:
        # Keep deep health informative, but cap dependency wait to avoid probe stalls.
        await asyncio.wait_for(
            asyncio.to_thread(qdrant_store.client.get_collections),
            timeout=1.5,
        )
    except Exception:
        qdrant_ok = False
    return {"status": "ok", "qdrant": "up" if qdrant_ok else "down"}
