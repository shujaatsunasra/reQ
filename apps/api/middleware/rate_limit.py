"""
Rate limiting middleware.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time

from core.config import settings
from core.redis import rate_limit_check
from core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    Limits requests per user per minute.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/live"]:
            return await call_next(request)
        
        # Get user identifier (from header, query param, or IP)
        user_id = (
            request.headers.get("X-User-ID") or
            request.query_params.get("user_id") or
            request.client.host if request.client else "anonymous"
        )
        
        # Check rate limit
        allowed, remaining = await rate_limit_check(
            user_id=user_id,
            limit=settings.rate_limit_per_minute
        )
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for user: {user_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {settings.rate_limit_per_minute} requests per minute."
                    }
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
