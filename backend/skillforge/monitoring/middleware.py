"""
FastAPI middleware for automatic metrics collection.
Wraps each request to record latency, status, and error details.
"""

from __future__ import annotations

import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from skillforge.monitoring.collector import MetricsCollector

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Automatically records HTTP request metrics:
    - Latency (ms)
    - Success/error counts
    - Error details
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics for monitoring endpoints themselves to avoid recursion
        if request.url.path.startswith("/api/v1/monitoring"):
            return await call_next(request)

        # Skip static file requests
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        start = time.time()
        response: Response | None = None

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            mc = MetricsCollector()
            latency = (time.time() - start) * 1000
            mc.record_request(latency_ms=latency, success=False)
            mc.record_error(
                code="INTERNAL_ERROR",
                message=str(exc)[:500],
            )
            raise
        finally:
            if response is not None:
                mc = MetricsCollector()
                latency = (time.time() - start) * 1000
                success = response.status_code < 400
                mc.record_request(latency_ms=latency, success=success)

                if not success:
                    mc.record_error(
                        code=f"HTTP_{response.status_code}",
                        message=f"{request.method} {request.url.path} → {response.status_code}",
                    )
