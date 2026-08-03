"""In-memory fallback-репозиторий агрегированной аналитики для локальной разработки без БД."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from app.modules.analytics.constants import ACTION_LABELS, SECTION_LABELS, TOP_ANALYTICS_LIMIT
from app.modules.analytics.domain.entities import (
    AnalyticsSectionClickEvent,
    AnalyticsSectionViewEvent,
    AnalyticsSessionEvent,
)
from app.modules.analytics.infrastructure.in_memory_store import InMemoryAnalyticsStore


def _label_for_day(value: datetime) -> str:
    """Преобразует datetime в подпись дня, совпадающую с форматом admin-графиков."""

    return value.astimezone(timezone.utc).strftime("%m-%d")


def _localized_label_for(key: str, labels: dict[str, dict[str, str]]) -> dict[str, str]:
    """Возвращает локализованную подпись или нейтральный fallback, если ключ еще не известен заранее."""

    return labels.get(key, {"ru": key, "en": key})


class InMemoryAnalyticsRepository:
    """Держит полностью обезличенные агрегаты в памяти процесса как fallback вместо PostgreSQL."""

    def __init__(self, analytics_store: InMemoryAnalyticsStore) -> None:
        self._analytics_store = analytics_store

    async def get_dashboard_snapshot(self) -> dict[str, object]:
        """Возвращает копию текущего in-memory snapshot, чтобы UI не мутировал состояние напрямую."""

        return deepcopy(self._analytics_store.dashboard_snapshot)

    async def ingest_session_event(
        self,
        event: AnalyticsSessionEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSessionEvent] | None = None,
    ) -> None:
        """Обновляет in-memory срез по анонимным сессиям."""

        self._increment_series(series_key="sessionsLast7Days", occurred_at=event.occurred_at, blocked=blocked)

        if not blocked:
            self._increment_total(total_key="sessions")

        if rollback_events:
            for rollback_event in rollback_events:
                self._decrement_series(series_key="sessionsLast7Days", occurred_at=rollback_event.occurred_at)
                self._decrement_total(total_key="sessions")

    async def ingest_section_view_event(
        self,
        event: AnalyticsSectionViewEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionViewEvent] | None = None,
    ) -> None:
        """Обновляет in-memory срез по просмотрам секций."""

        self._increment_series(series_key="viewsLast7Days", occurred_at=event.occurred_at, blocked=blocked)

        if not blocked:
            self._increment_total(total_key="sectionViews")
            self._increment_ranked_total(
                collection_key="topSections",
                item_key=event.section_key,
                labels=SECTION_LABELS,
            )

        if rollback_events:
            for rollback_event in rollback_events:
                self._decrement_series(series_key="viewsLast7Days", occurred_at=rollback_event.occurred_at)
                self._decrement_total(total_key="sectionViews")
                self._decrement_ranked_total(
                    collection_key="topSections",
                    item_key=rollback_event.section_key,
                    labels=SECTION_LABELS,
                )

    async def ingest_section_click_event(
        self,
        event: AnalyticsSectionClickEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionClickEvent] | None = None,
    ) -> None:
        """Обновляет in-memory срез по кликам действий."""

        self._increment_series(series_key="clicksLast7Days", occurred_at=event.occurred_at, blocked=blocked)

        if not blocked:
            self._increment_total(total_key="sectionClicks")
            self._increment_ranked_total(
                collection_key="topActions",
                item_key=event.action_key,
                labels=ACTION_LABELS,
            )

        if rollback_events:
            for rollback_event in rollback_events:
                self._decrement_series(series_key="clicksLast7Days", occurred_at=rollback_event.occurred_at)
                self._decrement_total(total_key="sectionClicks")
                self._decrement_ranked_total(
                    collection_key="topActions",
                    item_key=rollback_event.action_key,
                    labels=ACTION_LABELS,
                )

    def _sync_series_window(self, series_key: str, occurred_at: datetime) -> list[dict[str, object]]:
        """Поддерживает последние семь дней в фиксированном порядке даже в fallback-режиме."""

        snapshot = self._analytics_store.dashboard_snapshot
        existing_series = snapshot[series_key]
        existing_map = {
            str(series_item["label"]): {
                "label": str(series_item["label"]),
                "value": int(series_item["value"]),
                "blockedValue": int(series_item.get("blockedValue", 0)),
            }
            for series_item in existing_series
        }
        event_day = occurred_at.astimezone(timezone.utc).date()
        day_window = [event_day - timedelta(days=delta) for delta in range(6, -1, -1)]
        normalized_series = [
            existing_map.get(
                day_value.strftime("%m-%d"),
                {"label": day_value.strftime("%m-%d"), "value": 0, "blockedValue": 0},
            )
            for day_value in day_window
        ]
        snapshot[series_key] = normalized_series
        return normalized_series

    def _increment_series(self, series_key: str, occurred_at: datetime, blocked: bool) -> None:
        """Инкрементирует accepted или blocked часть нужного дневного графика."""

        normalized_series = self._sync_series_window(series_key=series_key, occurred_at=occurred_at)
        target_label = _label_for_day(occurred_at)

        for series_item in normalized_series:
            if series_item["label"] != target_label:
                continue

            if blocked:
                series_item["blockedValue"] = int(series_item.get("blockedValue", 0)) + 1
            else:
                series_item["value"] = int(series_item["value"]) + 1
            return

    def _decrement_series(self, series_key: str, occurred_at: datetime) -> None:
        """Откатывает ранее принятый accepted-счетчик в пределах видимого окна."""

        normalized_series = self._sync_series_window(series_key=series_key, occurred_at=occurred_at)
        target_label = _label_for_day(occurred_at)

        for series_item in normalized_series:
            if series_item["label"] == target_label:
                series_item["value"] = max(int(series_item["value"]) - 1, 0)
                return

    def _increment_total(self, total_key: str) -> None:
        """Инкрементирует all-time total без создания отдельных строк хранения."""

        total_collection = self._analytics_store.dashboard_snapshot["allTimeTotals"]
        total_collection[total_key] += 1

    def _decrement_total(self, total_key: str) -> None:
        """Откатывает ранее принятый all-time total после выявленного всплеска."""

        total_collection = self._analytics_store.dashboard_snapshot["allTimeTotals"]
        total_collection[total_key] = max(int(total_collection[total_key]) - 1, 0)

    def _increment_ranked_total(
        self,
        collection_key: str,
        item_key: str,
        labels: dict[str, dict[str, str]],
    ) -> None:
        """Инкрементирует рейтинг секций или действий с локализованной подписью."""

        collection = self._analytics_store.dashboard_snapshot[collection_key]

        for collection_item in collection:
            if collection_item["key"] == item_key:
                collection_item["total"] += 1
                self._sort_ranked_collection(collection_key=collection_key)
                return

        collection.append(
            {
                "key": item_key,
                "label": _localized_label_for(item_key, labels),
                "total": 1,
            }
        )
        self._sort_ranked_collection(collection_key=collection_key)

    def _decrement_ranked_total(
        self,
        collection_key: str,
        item_key: str,
        labels: dict[str, dict[str, str]],
    ) -> None:
        """Откатывает total у секции или действия и сохраняет компактный рейтинг."""

        collection = self._analytics_store.dashboard_snapshot[collection_key]

        for collection_item in collection:
            if collection_item["key"] == item_key:
                collection_item["total"] = max(int(collection_item["total"]) - 1, 0)
                self._sort_ranked_collection(collection_key=collection_key)
                return

        collection.append(
            {
                "key": item_key,
                "label": _localized_label_for(item_key, labels),
                "total": 0,
            }
        )
        self._sort_ranked_collection(collection_key=collection_key)

    def _sort_ranked_collection(self, collection_key: str) -> None:
        """Нормализует compact ranking так, чтобы админка всегда получала топ ограниченного размера."""

        collection = self._analytics_store.dashboard_snapshot[collection_key]
        sorted_collection = sorted(
            collection,
            key=lambda collection_item: (-int(collection_item["total"]), str(collection_item["key"])),
        )
        self._analytics_store.dashboard_snapshot[collection_key] = sorted_collection[:TOP_ANALYTICS_LIMIT]

