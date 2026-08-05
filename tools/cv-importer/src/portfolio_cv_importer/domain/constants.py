"""Константы import/export контура CV importer."""

from __future__ import annotations

PORTFOLIO_VERSION = "portfolio.v1"
PORTFOLIO_BUNDLE_VERSION = "portfolio.bundle.v1"
DEFAULT_AVATAR_PATH = "/media/photo_2025-04-09_22-18-09.jpg"
DEFAULT_SUPPORTED_LOCALES = ["en", "ru"]

SOURCE_FORMAT_PORTFOLIO_JSON = "portfolio_json"
SOURCE_FORMAT_PORTFOLIO_BUNDLE = "portfolio_bundle"
SOURCE_FORMAT_RESUME_PDF = "resume_pdf"
SOURCE_FORMAT_RESUME_MARKDOWN = "resume_markdown"
SOURCE_FORMAT_RESUME_TEXT = "resume_text"
SOURCE_FORMAT_RESUME_HTML = "resume_html"

TARGET_FORMAT_PORTFOLIO_JSON = "portfolio_json"
TARGET_FORMAT_PORTFOLIO_BUNDLE = "portfolio_bundle"
TARGET_FORMAT_RESUME_MARKDOWN = "resume_markdown"

RESUME_EXPORT_SECTION_TITLES = {
    "contacts": {
        "ru": "Контакты",
        "en": "Contacts",
    },
    "summary": {
        "ru": "Профиль",
        "en": "Profile",
    },
    "experience": {
        "ru": "Опыт работы",
        "en": "Experience",
    },
    "projects": {
        "ru": "Проекты",
        "en": "Projects",
    },
    "education": {
        "ru": "Образование",
        "en": "Education",
    },
    "skills": {
        "ru": "Ключевые направления",
        "en": "Core focus areas",
    },
}
