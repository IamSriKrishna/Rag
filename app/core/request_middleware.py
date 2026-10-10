import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.metrics import HTTP_DURATION, HTTP_REQUESTS

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise
        duration = time.perf_counter() - started
        route = request.scope.get("route")
        route_label = getattr(route, "path", "unmatched")
        HTTP_REQUESTS.labels(
            request.method, route_label, str(response.status_code)
        ).inc()
        HTTP_DURATION.labels(request.method, route_label).observe(duration)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed request_id=%s method=%s route=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            route_label,
            response.status_code,
            duration * 1000,
        )
        return response
