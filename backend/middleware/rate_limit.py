"""Rate limiting middleware for API endpoints."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitInfo:
    """Track rate limit info for a client."""

    def __init__(self, limit: int, window_seconds: int = 60):
        """
        Initialize rate limit tracker.

        Args:
            limit: Max requests allowed in window
            window_seconds: Time window in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: list[datetime] = []

    def is_allowed(self) -> bool:
        """Check if request is allowed and update counter."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Remove old requests outside the window
        self.requests = [req_time for req_time in self.requests if req_time > window_start]

        # Check if under limit
        if len(self.requests) < self.limit:
            self.requests.append(now)
            return True

        return False

    def remaining(self) -> int:
        """Get remaining requests in current window."""
        return max(0, self.limit - len(self.requests))

    def reset_at(self) -> datetime:
        """Get when the rate limit resets."""
        if not self.requests:
            return datetime.utcnow()

        oldest_request = min(self.requests)
        return oldest_request + timedelta(seconds=self.window_seconds)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.

    Tracks requests per IP address with configurable limits per endpoint.
    """

    def __init__(self, app, per_user_limit: int = 100, global_limit: int = 1000):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI app instance
            per_user_limit: Max requests per client per minute
            global_limit: Max total requests per minute (unused but configurable)
        """
        super().__init__(app)
        self.per_user_limit = per_user_limit
        self.global_limit = global_limit
        # Dict[ip_address, RateLimitInfo]
        self.rate_limits: Dict[str, RateLimitInfo] = defaultdict(
            lambda: RateLimitInfo(self.per_user_limit)
        )

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for certain endpoints
        path = request.url.path
        if path.startswith("/api/v1/lunar") or path == "/health":
            # Don't rate limit lunar or health endpoints
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Get rate limit for this client
        rate_limiter = self.rate_limits[client_ip]

        # Check if request is allowed
        if not rate_limiter.is_allowed():
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {request.url.path}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "remaining": 0,
                    "reset_at": rate_limiter.reset_at().isoformat(),
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limiter.remaining())
        response.headers["X-RateLimit-Reset"] = rate_limiter.reset_at().isoformat()

        return response
