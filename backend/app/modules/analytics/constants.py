"""Константы и локализованные подписи аналитики для admin dashboard."""

TOP_ANALYTICS_LIMIT = 3

SECTION_LABELS: dict[str, dict[str, str]] = {
    "hero": {"ru": "Hero-блок", "en": "Hero section"},
    "projects_grid": {"ru": "Сетка проектов", "en": "Projects grid"},
    "profile_summary": {"ru": "Краткое описание", "en": "Profile summary"},
}

ACTION_LABELS: dict[str, dict[str, str]] = {
    "open_projects": {"ru": "Открыть проекты", "en": "Open projects"},
    "read_intro": {"ru": "Озвучить вступление", "en": "Read intro aloud"},
    "switch_locale": {"ru": "Сменить язык", "en": "Switch locale"},
}

