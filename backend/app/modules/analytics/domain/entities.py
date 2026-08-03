"""Доменные сущности агрегированной анонимной аналитики."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class AnalyticsEventResult:
    """Результат ingest одного анонимного аналитического события."""

    status: str
    blocked_reason: str | None = None


@dataclass(slots=True, frozen=True)
class AnalyticsSessionEvent:
    """Полностью обезличенный агрегируемый факт старта сессии."""

    occurred_at: datetime
    entry_route_key: str
    locale_code: str
    consent_state: str
    storage_mode: str


@dataclass(slots=True, frozen=True)
class AnalyticsSectionViewEvent:
    """Полностью обезличенный агрегируемый факт просмотра секции."""

    occurred_at: datetime
    route_key: str
    section_key: str
    locale_code: str
    view_source: str


@dataclass(slots=True, frozen=True)
class AnalyticsSectionClickEvent:
    """Полностью обезличенный агрегируемый факт клика по действию."""

    occurred_at: datetime
    route_key: str
    section_key: str
    action_key: str
    locale_code: str


AnalyticsSpikePayload = AnalyticsSessionEvent | AnalyticsSectionViewEvent | AnalyticsSectionClickEvent


@dataclass(slots=True, frozen=True)
class AnalyticsTrackedEvent:
    """Краткоживущая in-memory запись для дедупликации и rollback всплесков без хранения сырых логов."""

    event_key: str
    occurred_at: datetime
    payload: AnalyticsSpikePayload
