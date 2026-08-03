"""Application-сервис полностью обезличенной агрегированной аналитики."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

from app.config.settings import Settings
from app.modules.analytics.domain.entities import (
    AnalyticsEventResult,
    AnalyticsSectionClickEvent,
    AnalyticsSectionViewEvent,
    AnalyticsSpikePayload,
    AnalyticsSessionEvent,
    AnalyticsTrackedEvent,
)
from app.modules.analytics.domain.repository import AnalyticsRepository
from app.modules.analytics.infrastructure.in_memory_store import InMemoryAnalyticsStore


class AnalyticsService:
    """Принимает анонимные события, дедуплицирует их, блокирует всплески и пишет только агрегаты."""

    def __init__(
        self,
        settings: Settings,
        analytics_repository: AnalyticsRepository,
        analytics_store: InMemoryAnalyticsStore,
    ) -> None:
        self._settings = settings
        self._analytics_repository = analytics_repository
        self._analytics_store = analytics_store

    async def get_dashboard_snapshot(self) -> dict[str, object]:
        """Возвращает текущий snapshot admin-аналитики из основного источника или fallback."""

        return await self._analytics_repository.get_dashboard_snapshot()

    async def register_session_event(
        self,
        entry_route_key: str,
        locale_code: str,
        consent_state: str,
        storage_mode: str,
        session_nonce: str,
    ) -> AnalyticsEventResult:
        """Учитывает старт анонимной сессии после подтвержденного consent."""

        if consent_state != "accepted":
            return AnalyticsEventResult(status="blocked", blocked_reason="consent_required")

        now = datetime.now(tz=timezone.utc)
        session_event = AnalyticsSessionEvent(
            occurred_at=now,
            entry_route_key=entry_route_key,
            locale_code=locale_code,
            consent_state=consent_state,
            storage_mode=storage_mode,
        )
        event_key = f"session:{entry_route_key}:{locale_code}:{storage_mode}:{session_nonce}"
        spike_key = f"session:{entry_route_key}:{locale_code}"

        if self._is_duplicate(event_key=event_key, now=now):
            return AnalyticsEventResult(status="deduplicated")

        rollback_events = self._consume_spike_bucket(spike_key=spike_key, now=now)

        if rollback_events is not None:
            await self._analytics_repository.ingest_session_event(
                event=session_event,
                blocked=True,
                rollback_events=rollback_events,
            )
            return AnalyticsEventResult(status="blocked", blocked_reason="spike_threshold")

        await self._analytics_repository.ingest_session_event(event=session_event, blocked=False)
        self._remember_event(event_key=event_key, now=now)
        self._append_tracked_event(spike_key=spike_key, event_key=event_key, now=now, payload=session_event)
        return AnalyticsEventResult(status="accepted")

    async def register_section_view_event(
        self,
        route_key: str,
        section_key: str,
        locale_code: str,
        view_source: str,
        session_nonce: str,
    ) -> AnalyticsEventResult:
        """Учитывает просмотр секции после SSR/hydration-события без хранения сырого access log."""

        now = datetime.now(tz=timezone.utc)
        section_view_event = AnalyticsSectionViewEvent(
            occurred_at=now,
            route_key=route_key,
            section_key=section_key,
            locale_code=locale_code,
            view_source=view_source,
        )
        event_key = f"view:{route_key}:{section_key}:{locale_code}:{view_source}:{session_nonce}"
        spike_key = f"view:{route_key}:{section_key}:{locale_code}"

        if self._is_duplicate(event_key=event_key, now=now):
            return AnalyticsEventResult(status="deduplicated")

        rollback_events = self._consume_spike_bucket(spike_key=spike_key, now=now)

        if rollback_events is not None:
            await self._analytics_repository.ingest_section_view_event(
                event=section_view_event,
                blocked=True,
                rollback_events=rollback_events,
            )
            return AnalyticsEventResult(status="blocked", blocked_reason="spike_threshold")

        await self._analytics_repository.ingest_section_view_event(event=section_view_event, blocked=False)
        self._remember_event(event_key=event_key, now=now)
        self._append_tracked_event(
            spike_key=spike_key,
            event_key=event_key,
            now=now,
            payload=section_view_event,
        )
        return AnalyticsEventResult(status="accepted")

    async def register_section_click_event(
        self,
        route_key: str,
        section_key: str,
        action_key: str,
        locale_code: str,
        session_nonce: str,
    ) -> AnalyticsEventResult:
        """Учитывает клик по действию без хранения сырого access log и без user-привязки."""

        now = datetime.now(tz=timezone.utc)
        section_click_event = AnalyticsSectionClickEvent(
            occurred_at=now,
            route_key=route_key,
            section_key=section_key,
            action_key=action_key,
            locale_code=locale_code,
        )
        event_key = f"click:{route_key}:{section_key}:{action_key}:{locale_code}:{session_nonce}"
        spike_key = f"click:{route_key}:{section_key}:{action_key}:{locale_code}"

        if self._is_duplicate(event_key=event_key, now=now):
            return AnalyticsEventResult(status="deduplicated")

        rollback_events = self._consume_spike_bucket(spike_key=spike_key, now=now)

        if rollback_events is not None:
            await self._analytics_repository.ingest_section_click_event(
                event=section_click_event,
                blocked=True,
                rollback_events=rollback_events,
            )
            return AnalyticsEventResult(status="blocked", blocked_reason="spike_threshold")

        await self._analytics_repository.ingest_section_click_event(event=section_click_event, blocked=False)
        self._remember_event(event_key=event_key, now=now)
        self._append_tracked_event(
            spike_key=spike_key,
            event_key=event_key,
            now=now,
            payload=section_click_event,
        )
        return AnalyticsEventResult(status="accepted")

    def _is_duplicate(self, event_key: str, now: datetime) -> bool:
        """Проверяет дедупликацию в коротком окне и очищает просроченные записи."""

        self._prune_recent_events(now=now)
        dedupe_window = timedelta(seconds=self._settings.analytics_event_dedupe_window_seconds)
        recent_event_time = self._analytics_store.recent_events.get(event_key)
        return recent_event_time is not None and now - recent_event_time < dedupe_window

    def _remember_event(self, event_key: str, now: datetime) -> None:
        """Сохраняет краткоживущий ключ принятого события только для дедупликации."""

        self._analytics_store.recent_events[event_key] = now

    def _prune_recent_events(self, now: datetime) -> None:
        """Удаляет из памяти старые dedupe-ключи, чтобы процесс не накапливал мусор."""

        dedupe_window = timedelta(seconds=self._settings.analytics_event_dedupe_window_seconds)
        stale_event_keys = [
            event_key
            for event_key, occurred_at in self._analytics_store.recent_events.items()
            if now - occurred_at > dedupe_window
        ]

        for stale_event_key in stale_event_keys:
            self._analytics_store.recent_events.pop(stale_event_key, None)

    def _consume_spike_bucket(
        self,
        spike_key: str,
        now: datetime,
    ) -> list[AnalyticsSessionEvent] | list[AnalyticsSectionViewEvent] | list[AnalyticsSectionClickEvent] | None:
        """Возвращает принятые события окна для rollback, если обнаружен резкий подозрительный всплеск."""

        spike_window = timedelta(seconds=self._settings.analytics_spike_window_seconds)
        spike_bucket = self._analytics_store.spike_buckets.setdefault(spike_key, deque())

        while spike_bucket and now - spike_bucket[0].occurred_at > spike_window:
            spike_bucket.popleft()

        if len(spike_bucket) < self._settings.analytics_spike_threshold:
            return None

        rollback_events = [tracked_event.payload for tracked_event in spike_bucket]
        spike_bucket.clear()
        return rollback_events

    def _append_tracked_event(
        self,
        spike_key: str,
        event_key: str,
        now: datetime,
        payload: AnalyticsSpikePayload,
    ) -> None:
        """Добавляет принятое событие в короткоживущее окно антиспайк-защиты."""

        spike_bucket = self._analytics_store.spike_buckets.setdefault(spike_key, deque())
        spike_bucket.append(
            AnalyticsTrackedEvent(
                event_key=event_key,
                occurred_at=now,
                payload=payload,
            )
        )
