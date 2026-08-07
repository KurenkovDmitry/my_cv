"""Тесты исключения служебных посещений из публичной аналитики."""

from app.modules.analytics.api.traffic_filter import resolve_analytics_ignore_reason


def test_admin_session_is_not_counted_as_public_visitor() -> None:
    assert resolve_analytics_ignore_reason(
        environment="production",
        track_non_production=False,
        user_agent="Mozilla/5.0",
        marked_as_test=False,
        has_admin_session=True,
    ) == "admin_session"


def test_headless_browser_is_not_counted_in_production() -> None:
    assert resolve_analytics_ignore_reason(
        environment="production",
        track_non_production=False,
        user_agent="Mozilla/5.0 HeadlessChrome/140.0",
        marked_as_test=False,
        has_admin_session=False,
    ) == "automation_traffic"


def test_development_traffic_is_disabled_by_default() -> None:
    assert resolve_analytics_ignore_reason(
        environment="development",
        track_non_production=False,
        user_agent="Mozilla/5.0",
        marked_as_test=False,
        has_admin_session=False,
    ) == "non_production"


def test_regular_production_browser_is_counted() -> None:
    assert resolve_analytics_ignore_reason(
        environment="production",
        track_non_production=False,
        user_agent="Mozilla/5.0 Firefox/141.0",
        marked_as_test=False,
        has_admin_session=False,
    ) is None
