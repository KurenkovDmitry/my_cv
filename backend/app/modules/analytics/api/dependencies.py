"""Dependency-фабрики агрегированной аналитики."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.session import get_read_database_session, get_write_database_session
from app.modules.analytics.application.service import AnalyticsService
from app.modules.analytics.infrastructure.in_memory_repository import InMemoryAnalyticsRepository
from app.modules.analytics.infrastructure.in_memory_store import InMemoryAnalyticsStore
from app.modules.analytics.infrastructure.sqlalchemy_repository import (
    FallbackAnalyticsRepository,
    SqlAlchemyAnalyticsRepository,
)

_analytics_store = InMemoryAnalyticsStore()


def get_analytics_summary_service(
    read_database_session: AsyncSession = Depends(get_read_database_session),
) -> AnalyticsService:
    """Собирает analytics-service для read-path графиков админки."""

    primary_repository = SqlAlchemyAnalyticsRepository(read_database_session=read_database_session)
    fallback_repository = InMemoryAnalyticsRepository(analytics_store=_analytics_store)
    return AnalyticsService(
        settings=get_settings(),
        analytics_repository=FallbackAnalyticsRepository(
            primary_repository=primary_repository,
            fallback_repository=fallback_repository,
        ),
        analytics_store=_analytics_store,
    )


def get_analytics_event_service(
    write_database_session: AsyncSession = Depends(get_write_database_session),
) -> AnalyticsService:
    """Собирает analytics-service для mutation-path анонимных ingest-событий."""

    primary_repository = SqlAlchemyAnalyticsRepository(write_database_session=write_database_session)
    fallback_repository = InMemoryAnalyticsRepository(analytics_store=_analytics_store)
    return AnalyticsService(
        settings=get_settings(),
        analytics_repository=FallbackAnalyticsRepository(
            primary_repository=primary_repository,
            fallback_repository=fallback_repository,
        ),
        analytics_store=_analytics_store,
    )
