"""In-memory store для fallback-аналитики и краткоживущей антиспайк-защиты."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.modules.analytics.domain.entities import AnalyticsTrackedEvent


def _today_label() -> str:
    """Возвращает label сегодняшнего дня в формате, удобном для preview-графиков."""

    return datetime.now(tz=timezone.utc).strftime("%m-%d")


@dataclass(slots=True)
class InMemoryAnalyticsStore:
    """Хранит только краткоживущие event-ключи и fallback-агрегаты внутри процесса."""

    recent_events: dict[str, datetime] = field(default_factory=dict)
    spike_buckets: dict[str, deque[AnalyticsTrackedEvent]] = field(default_factory=lambda: defaultdict(deque))
    dashboard_snapshot: dict[str, object] = field(
        default_factory=lambda: {
            "sessionsLast7Days": [
                {"label": "07-28", "value": 12, "blockedValue": 1},
                {"label": "07-29", "value": 18, "blockedValue": 0},
                {"label": "07-30", "value": 16, "blockedValue": 0},
                {"label": "07-31", "value": 21, "blockedValue": 1},
                {"label": "08-01", "value": 26, "blockedValue": 2},
                {"label": "08-02", "value": 24, "blockedValue": 1},
                {"label": _today_label(), "value": 29, "blockedValue": 1},
            ],
            "viewsLast7Days": [
                {"label": "07-28", "value": 64, "blockedValue": 2},
                {"label": "07-29", "value": 82, "blockedValue": 3},
                {"label": "07-30", "value": 79, "blockedValue": 1},
                {"label": "07-31", "value": 88, "blockedValue": 2},
                {"label": "08-01", "value": 102, "blockedValue": 4},
                {"label": "08-02", "value": 98, "blockedValue": 2},
                {"label": _today_label(), "value": 117, "blockedValue": 3},
            ],
            "clicksLast7Days": [
                {"label": "07-28", "value": 14, "blockedValue": 0},
                {"label": "07-29", "value": 18, "blockedValue": 1},
                {"label": "07-30", "value": 21, "blockedValue": 0},
                {"label": "07-31", "value": 23, "blockedValue": 1},
                {"label": "08-01", "value": 31, "blockedValue": 1},
                {"label": "08-02", "value": 28, "blockedValue": 0},
                {"label": _today_label(), "value": 34, "blockedValue": 1},
            ],
            "topSections": [
                {"key": "hero", "label": {"ru": "Hero-блок", "en": "Hero section"}, "total": 482},
                {"key": "projects_grid", "label": {"ru": "Сетка проектов", "en": "Projects grid"}, "total": 316},
                {"key": "profile_summary", "label": {"ru": "Краткое описание", "en": "Profile summary"}, "total": 244},
            ],
            "topActions": [
                {"key": "open_projects", "label": {"ru": "Открыть проекты", "en": "Open projects"}, "total": 98},
                {"key": "read_intro", "label": {"ru": "Озвучить вступление", "en": "Read intro aloud"}, "total": 44},
                {"key": "switch_locale", "label": {"ru": "Сменить язык", "en": "Switch locale"}, "total": 32},
            ],
            "allTimeTotals": {
                "sessions": 1462,
                "sectionViews": 8124,
                "sectionClicks": 1198,
            },
        }
    )
