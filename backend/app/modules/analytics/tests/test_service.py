"""Unit-тесты application-сервиса агрегированной аналитики."""

from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.modules.analytics.application.service import AnalyticsService
from app.modules.analytics.infrastructure.in_memory_store import InMemoryAnalyticsStore


class RecordingAnalyticsRepository:
    """Запоминает вызовы репозитория, чтобы проверить дедупликацию и rollback без реальной БД."""

    def __init__(self) -> None:
        self.session_calls: list[dict[str, object]] = []
        self.section_view_calls: list[dict[str, object]] = []
        self.section_click_calls: list[dict[str, object]] = []

    async def get_dashboard_snapshot(self) -> dict[str, object]:
        """Возвращает пустой snapshot, который не используется в этих тестах."""

        return {}

    async def ingest_session_event(self, event, blocked=False, rollback_events=None) -> None:  # type: ignore[no-untyped-def]
        """Запоминает mutation-path по сессиям."""

        self.session_calls.append(
            {
                "event": event,
                "blocked": blocked,
                "rollback_events": rollback_events or [],
            }
        )

    async def ingest_section_view_event(self, event, blocked=False, rollback_events=None) -> None:  # type: ignore[no-untyped-def]
        """Запоминает mutation-path по просмотрам секций."""

        self.section_view_calls.append(
            {
                "event": event,
                "blocked": blocked,
                "rollback_events": rollback_events or [],
            }
        )

    async def ingest_section_click_event(self, event, blocked=False, rollback_events=None) -> None:  # type: ignore[no-untyped-def]
        """Запоминает mutation-path по кликам действий."""

        self.section_click_calls.append(
            {
                "event": event,
                "blocked": blocked,
                "rollback_events": rollback_events or [],
            }
        )


@pytest.mark.asyncio
async def test_analytics_service_deduplicates_same_session_event() -> None:
    """Проверяет, что повтор одного и того же session-события в коротком окне не дублирует агрегаты."""

    repository = RecordingAnalyticsRepository()
    analytics_service = AnalyticsService(
        settings=Settings(
            ANALYTICS_EVENT_DEDUPE_WINDOW_SECONDS=60,
            ANALYTICS_SPIKE_THRESHOLD=20,
            ANALYTICS_SPIKE_WINDOW_SECONDS=60,
        ),
        analytics_repository=repository,  # type: ignore[arg-type]
        analytics_store=InMemoryAnalyticsStore(),
    )

    first_result = await analytics_service.register_session_event(
        entry_route_key="/",
        locale_code="ru",
        consent_state="accepted",
        storage_mode="local_storage",
        session_nonce="same-session",
    )
    second_result = await analytics_service.register_session_event(
        entry_route_key="/projects",
        locale_code="en",
        consent_state="accepted",
        storage_mode="local_storage",
        session_nonce="same-session",
    )

    assert first_result.status == "accepted"
    assert second_result.status == "deduplicated"
    assert len(repository.session_calls) == 1
    assert repository.session_calls[0]["blocked"] is False


@pytest.mark.asyncio
async def test_analytics_service_rolls_back_spike_bucket_for_clicks() -> None:
    """Проверяет, что резкий всплеск кликов блокируется и откатывает ранее принятые события окна."""

    repository = RecordingAnalyticsRepository()
    analytics_service = AnalyticsService(
        settings=Settings(
            ANALYTICS_EVENT_DEDUPE_WINDOW_SECONDS=1,
            ANALYTICS_SPIKE_THRESHOLD=2,
            ANALYTICS_SPIKE_WINDOW_SECONDS=60,
        ),
        analytics_repository=repository,  # type: ignore[arg-type]
        analytics_store=InMemoryAnalyticsStore(),
    )

    first_result = await analytics_service.register_section_click_event(
        route_key="/",
        section_key="hero",
        action_key="open_projects",
        locale_code="ru",
        session_nonce="session-1",
    )
    second_result = await analytics_service.register_section_click_event(
        route_key="/",
        section_key="hero",
        action_key="open_projects",
        locale_code="ru",
        session_nonce="session-2",
    )
    third_result = await analytics_service.register_section_click_event(
        route_key="/",
        section_key="hero",
        action_key="open_projects",
        locale_code="ru",
        session_nonce="session-3",
    )

    assert first_result.status == "accepted"
    assert second_result.status == "accepted"
    assert third_result.status == "blocked"
    assert third_result.blocked_reason == "spike_threshold"
    assert len(repository.section_click_calls) == 3
    assert repository.section_click_calls[0]["blocked"] is False
    assert repository.section_click_calls[1]["blocked"] is False
    assert repository.section_click_calls[2]["blocked"] is True
    assert len(repository.section_click_calls[2]["rollback_events"]) == 2
