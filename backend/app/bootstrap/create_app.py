"""Фабрика FastAPI-приложения."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.middleware.request_context import RequestContextMiddleware
from app.modules.analytics.api.router import router as analytics_router
from app.modules.content.api.admin_router import router as admin_content_router
from app.modules.content.api.router import router as content_router
from app.modules.localization.api.router import router as localization_router
from app.modules.profile.api.router import router as profile_router
from app.modules.projects.api.router import router as projects_router
from app.modules.system.api.router import router as system_router


def create_app() -> FastAPI:
    """Создаёт экземпляр FastAPI с безопасной базовой конфигурацией."""

    settings = get_settings()
    application = FastAPI(
        title="Portfolio API",
        version="0.1.0",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )
    application.add_middleware(RequestContextMiddleware)

    @application.get("/health/live", tags=["system"])
    async def live_healthcheck() -> dict[str, str]:
        """Используется для liveness probe."""

        return {"status": "ok"}

    application.include_router(profile_router, prefix="/api/public")
    application.include_router(projects_router, prefix="/api/public")
    application.include_router(localization_router, prefix="/api/public")
    application.include_router(content_router, prefix="/api/public")
    application.include_router(analytics_router, prefix="/api/public")
    application.include_router(admin_content_router, prefix="/api/admin")
    application.include_router(analytics_router, prefix="/api/admin")
    application.include_router(system_router, prefix="/api/admin")

    return application
