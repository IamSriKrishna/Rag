from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.request_middleware import RequestLoggingMiddleware
from app.services.cache_service import CacheService
from app.services.rag_service import RAGService

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.prepare_directories()
    app.state.rag_service = RAGService()
    app.state.cache_service = CacheService()
    yield
    app.state.cache_service.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
