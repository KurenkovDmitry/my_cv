"""Контракты репозиториев агрегированной анонимной аналитики."""

from __future__ import annotations

from typing import Protocol

from app.modules.analytics.domain.entities import (
    AnalyticsSectionClickEvent,
    AnalyticsSectionViewEvent,
    AnalyticsSessionEvent,
)


class AnalyticsRepository(Protocol):
    """Описывает read/write-контракт анонимной агрегированной аналитики без сырых логов."""

    async def get_dashboard_snapshot(self) -> dict[str, object]:
        """Возвращает агрегированный снимок графиков и total-метрик для админки."""

    async def ingest_session_event(
        self,
        event: AnalyticsSessionEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSessionEvent] | None = None,
    ) -> None:
        """Фиксирует анонимную сессию или факт ее блокировки/отката в агрегатах."""

    async def ingest_section_view_event(
        self,
        event: AnalyticsSectionViewEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionViewEvent] | None = None,
    ) -> None:
        """Фиксирует просмотр секции или его блокировку/откат в агрегатах."""

    async def ingest_section_click_event(
        self,
        event: AnalyticsSectionClickEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionClickEvent] | None = None,
    ) -> None:
        """Фиксирует клик по действию или его блокировку/откат в агрегатах."""

