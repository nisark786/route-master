from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from app.routes.ai import router as ai_router
from app.routes.health import router as health_router
from app.services.qdrant_store import qdrant_store

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version
)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.on_event("startup")
def on_startup() -> None:
    qdrant_store.ensure_collection()


app.include_router(health_router)
app.include_router(ai_router)
