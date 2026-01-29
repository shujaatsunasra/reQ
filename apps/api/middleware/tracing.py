"""
Distributed tracing middleware using OpenTelemetry.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Distributed tracing middleware.
    Adds trace IDs and timing information to requests.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or extract trace ID
        trace_id = (
            request.headers.get("X-Trace-ID") or
            request.headers.get("traceparent", "").split("-")[1] if "traceparent" in request.headers else None or
            str(uuid.uuid4())
        )
        
        # Add to request state
        request.state.trace_id = trace_id
        request.state.start_time = time.time()
        
        # Log request
        logger.info(
            f"[{trace_id}] {request.method} {request.url.path}",
            extra={"trace_id": trace_id}
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - request.state.start_time) * 1000
            
            # Add trace headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Log response
            logger.info(
                f"[{trace_id}] {response.status_code} {duration_ms:.2f}ms",
                extra={"trace_id": trace_id, "duration_ms": duration_ms}
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - request.state.start_time) * 1000
            logger.error(
                f"[{trace_id}] Error: {str(e)} ({duration_ms:.2f}ms)",
                extra={"trace_id": trace_id, "duration_ms": duration_ms, "error": str(e)}
            )
            raise
