import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from app.routes.ai import router as ai_router
from app.routes.health import router as health_router
from app.services.qdrant_store import qdrant_store

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version
)

if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

logger = logging.getLogger(__name__)


@app.on_event("startup")
def on_startup() -> None:
    # Qdrant can start slightly later than this service in Kubernetes.
    # Retry a few times and keep the API process alive even if bootstrap fails,
    # so the pod does not crash-loop during rollout.
    max_attempts = 12
    for attempt in range(1, max_attempts + 1):
        try:
            qdrant_store.ensure_collection()
            logger.info("Qdrant bootstrap completed on attempt %s", attempt)
            return
        except Exception as exc:
            if attempt == max_attempts:
                logger.warning(
                    "Qdrant bootstrap failed after %s attempts; service will continue and retry on demand. Error: %s",
                    max_attempts,
                    exc,
                )
                return
            sleep_seconds = min(2 * attempt, 15)
            logger.warning(
                "Qdrant not ready (attempt %s/%s). Retrying in %ss. Error: %s",
                attempt,
                max_attempts,
                sleep_seconds,
                exc,
            )
            time.sleep(sleep_seconds)


app.include_router(health_router)
app.include_router(ai_router)
