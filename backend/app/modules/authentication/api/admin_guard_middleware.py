"""Middleware защиты всего административного API."""

from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.modules.authentication.application.admin_access_throttle import (
    AdminThrottleExceededError,
    get_admin_access_throttle,
)
from app.modules.authentication.application.admin_session_service import get_admin_session_service


class AdminGuardMiddleware(BaseHTTPMiddleware):
    """Требует действующую административную сессию для всех `/api/admin/*` маршрутов."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._admin_access_throttle = get_admin_access_throttle()
        self._admin_session_service = get_admin_session_service()

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        """Проверяет авторизацию, CSRF и rate-limit административного HTTP-запроса."""

        if not request.url.path.startswith("/api/admin"):
            return await call_next(request)

        if request.url.path.startswith("/api/admin/auth"):
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        try:
            self._admin_access_throttle.register_admin_api_request(client_ip=client_ip)
        except AdminThrottleExceededError as error:
            return JSONResponse(
                status_code=429,
                content={
                    "code": "ADMIN_API_RATE_LIMIT_EXCEEDED",
                    "message": str(error),
                    "retryAfterSeconds": error.retry_after_seconds,
                },
                headers={"Retry-After": str(error.retry_after_seconds)},
            )

        admin_session = self._admin_session_service.read_session_from_request(request)
        if admin_session is None:
            return JSONResponse(
                status_code=401,
                content={
                    "code": "ADMIN_AUTH_REQUIRED",
                    "message": "Administrative session is required.",
                },
            )

        if request.method not in {"GET", "HEAD"}:
            csrf_header = request.headers.get("X-CSRF-Token", "")
            if not csrf_header or not hmac.compare_digest(csrf_header, admin_session.csrf_token):
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": "ADMIN_CSRF_VALIDATION_FAILED",
                        "message": "Administrative CSRF token is invalid or missing.",
                    },
                )

        request.state.admin_login = admin_session.login
        request.state.admin_session_expires_at = admin_session.expires_at
        request.state.admin_csrf_token = admin_session.csrf_token
        return await call_next(request)
