"""Фильтрация служебного трафика до записи аналитических агрегатов."""

from __future__ import annotations

_AUTOMATION_USER_AGENT_MARKERS = (
    "headlesschrome",
    "playwright",
    "cypress",
    "selenium",
    "pytest",
    "vitest",
)


def resolve_analytics_ignore_reason(
    *,
    environment: str,
    track_non_production: bool,
    user_agent: str,
    marked_as_test: bool,
    has_admin_session: bool,
) -> str | None:
    """Возвращает причину исключения события или ``None`` для реального посетителя."""

    if marked_as_test:
        return "test_traffic"
    if has_admin_session:
        return "admin_session"
    if environment.strip().lower() != "production" and not track_non_production:
        return "non_production"
    normalized_user_agent = user_agent.strip().lower()
    if any(marker in normalized_user_agent for marker in _AUTOMATION_USER_AGENT_MARKERS):
        return "automation_traffic"
    return None
