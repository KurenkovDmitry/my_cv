"""In-memory store для fallback-аналитики и краткоживущей антиспайк-защиты."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.modules.analytics.domain.entities import AnalyticsTrackedEvent


def _empty_daily_series() -> list[dict[str, int | str]]:
    """Возвращает честную нулевую неделю вместо демонстрационных посещений."""

    today = datetime.now(tz=timezone.utc).date()
    return [
        {
            "label": (today - timedelta(days=day_offset)).strftime("%m-%d"),
            "value": 0,
            "blockedValue": 0,
        }
        for day_offset in range(6, -1, -1)
    ]


@dataclass(slots=True)
class InMemoryAnalyticsStore:
    """Хранит только краткоживущие event-ключи и fallback-агрегаты внутри процесса."""

    recent_events: dict[str, datetime] = field(default_factory=dict)
    spike_buckets: dict[str, deque[AnalyticsTrackedEvent]] = field(default_factory=lambda: defaultdict(deque))
    dashboard_snapshot: dict[str, object] = field(
        default_factory=lambda: {
            "sourceKind": "memory_fallback",
            "sessionsLast7Days": _empty_daily_series(),
            "viewsLast7Days": _empty_daily_series(),
            "clicksLast7Days": _empty_daily_series(),
            "topSections": [],
            "topActions": [],
            "allTimeTotals": {
                "sessions": 0,
                "sectionViews": 0,
                "sectionClicks": 0,
            },
        }
    )
