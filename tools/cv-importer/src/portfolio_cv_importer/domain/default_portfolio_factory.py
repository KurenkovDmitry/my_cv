"""Фабрика базового каркаса `portfolio.v1`."""

from __future__ import annotations

from portfolio_cv_importer.domain.constants import (
    DEFAULT_AVATAR_PATH,
    DEFAULT_SUPPORTED_LOCALES,
    PORTFOLIO_VERSION,
)


def create_base_portfolio_payload(
    *,
    display_name_ru: str,
    display_name_en: str,
    headline_ru: str,
    headline_en: str,
    location_ru: str,
    location_en: str,
) -> dict[str, object]:
    """Создаёт безопасный стартовый payload, поверх которого накладываются данные резюме."""

    return {
        "version": PORTFOLIO_VERSION,
        "draft": True,
        "needsManualReview": True,
        "profile": {
            "slug": "primary",
            "displayName": {
                "ru": display_name_ru or "Дмитрий Андреевич Куренков",
                "en": display_name_en or "Dmitry Andreevich Kurenkov",
            },
            "headline": {
                "ru": headline_ru or "Системный аналитик и platform-инженер, который проектирует highload-сервисы, данные и рабочие интерфейсы.",
                "en": headline_en or "System analyst and platform-minded engineer focused on highload services, data architecture, and production-grade interfaces.",
            },
            "summary": {
                "ru": "Строю архитектуру вокруг нагрузки, интеграций и эксплуатационной устойчивости: от требований и моделей данных до backend-контуров, CI/CD и админ-панелей.",
                "en": "I build architecture around load, integrations, and operational resilience, spanning requirements, data models, backend services, CI/CD, and admin tooling.",
            },
            "location": {
                "ru": location_ru or "Россия, Москва",
                "en": location_en or "Moscow, Russia",
            },
            "avatarAsset": DEFAULT_AVATAR_PATH,
        },
        "education": [],
        "projects": [],
        "experience": [],
        "skills": {
            "focusAreas": [
                "System analysis",
                "Highload architecture",
                "Microservices",
                "Backend platform engineering",
                "Admin panels",
                "Data modeling",
                "CI/CD",
            ],
        },
        "themes": {
            "active": "engineering-blueprint",
            "available": [
                {
                    "id": "engineering-blueprint",
                    "label": {
                        "ru": "Инженерный blueprint",
                        "en": "Engineering blueprint",
                    },
                },
                {
                    "id": "papyrus-scroll",
                    "label": {
                        "ru": "Папирусный свиток",
                        "en": "Papyrus scroll",
                    },
                },
            ],
        },
        "localization": {
            "defaultLocale": "en",
            "supportedLocales": DEFAULT_SUPPORTED_LOCALES,
            "autoDetectByRegion": {
                "RU": "ru",
            },
        },
        "accessibility": {
            "speechSynthesisEnabled": True,
            "highContrastModeEnabled": True,
            "reducedMotionPresetEnabled": True,
        },
        "legal": {
            "analyticsConsent": {
                "version": "2026-08-05",
                "modalTitle": {
                    "ru": "Согласие на обезличенную аналитику",
                    "en": "Consent for anonymous analytics",
                },
                "modalBodyMarkdown": {
                    "ru": "Сайт собирает только обезличенные агрегированные события по просмотрам, кликам и сеансам без привязки к личности и постоянному идентификатору устройства.",
                    "en": "The site stores only anonymous aggregated events about views, clicks, and sessions without tying them to identity or a permanent device identifier.",
                },
                "acceptButtonLabel": {
                    "ru": "Продолжить и согласиться",
                    "en": "Continue and agree",
                },
                "rejectButtonLabel": {
                    "ru": "Отказаться и закрыть сайт",
                    "en": "Decline and close site",
                },
            },
        },
        "seo": {
            "siteName": {
                "ru": "Портфолио Дмитрия Куренкова",
                "en": "Dmitry Kurenkov Portfolio",
            },
            "openGraphImage": DEFAULT_AVATAR_PATH,
        },
    }
