"""Временный preview-репозиторий для контентного snapshot-модуля."""

from copy import deepcopy

from app.modules.content.domain.entities import PortfolioSnapshotRecord


def build_preview_payload(snapshot_kind: str) -> dict[str, object]:
    """Строит preview payload для published или draft snapshot."""

    is_draft = snapshot_kind == "draft"

    payload = {
        "version": "portfolio.v1",
        "draft": is_draft,
        "needsManualReview": is_draft,
        "profile": {
            "slug": "primary",
            "displayName": {
                "ru": "Д. А. Куренков",
                "en": "D. A. Kurenkov",
            },
            "headline": {
                "ru": "Инженер, соединяющий highload-мышление, инфраструктуру и аккуратный интерфейс.",
                "en": "An engineer connecting highload thinking, infrastructure, and refined interface design.",
            },
            "summary": {
                "ru": "SSR-слепок уже подготовлен как единый документ для быстрой первой выдачи."
                if not is_draft
                else "Черновик уже собран в единую структуру и готов к выборочной замене через import candidate.",
                "en": "The SSR snapshot is already prepared as a single document for fast first paint."
                if not is_draft
                else "The draft snapshot is already unified and ready for selective replacement through the import candidate flow.",
            },
            "location": {
                "ru": "Россия",
                "en": "Russia",
            },
            "avatarAsset": "/rules/photo_2025-04-09_22-18-09.jpg",
        },
        "education": [
            {
                "id": "bmstu",
                "title": {
                    "ru": "МГТУ имени Н. Э. Баумана",
                    "en": "Bauman Moscow State Technical University",
                },
                "status": "published" if not is_draft else "needs_review",
            }
        ],
        "projects": [
            {
                "id": "portfolio-platform",
                "slug": "portfolio-platform",
                "featured": True,
                "status": "active",
                "title": {
                    "ru": "Платформа персонального портфолио",
                    "en": "Personal portfolio platform",
                },
                "summary": {
                    "ru": "Публичная витрина, админка, агрегированная аналитика и импорт контента из резюме."
                    if not is_draft
                    else "Черновой проектный блок для дальнейшей разметки, selective replace и publish.",
                    "en": "A public showcase, admin panel, aggregated analytics, and resume-driven content import."
                    if not is_draft
                    else "A draft project block prepared for further markup, selective replace, and publish.",
                },
                "technologies": [
                    "TypeScript",
                    "React",
                    "FastAPI",
                    "PostgreSQL",
                    "Redis",
                ],
                "links": [
                    {
                        "kind": "repository",
                        "label": {
                            "ru": "Исходный код",
                            "en": "Source code",
                        },
                        "href": "#",
                    }
                ],
            }
        ],
        "experience": [
            {
                "id": "resume-import",
                "company": {
                    "ru": "Импорт из резюме подключается",
                    "en": "Resume import is being connected",
                },
                "role": {
                    "ru": "Старые версии хранятся в export bundle, а не в БД.",
                    "en": "Older versions are stored as export bundles rather than in the database.",
                },
                "status": "published" if not is_draft else "needs_review",
            }
        ],
        "skills": {
            "focusAreas": [
                "Highload architecture",
                "Infrastructure",
                "SSR delivery",
                "Observability",
            ]
        },
        "themes": {
            "active": "paper-sand",
            "available": [
                {
                    "id": "paper-sand",
                    "label": {
                        "ru": "Тёплый песок",
                        "en": "Paper sand",
                    },
                },
                {
                    "id": "contrast-carbon",
                    "label": {
                        "ru": "Контрастный графит",
                        "en": "Contrast carbon",
                    },
                },
            ],
        },
        "localization": {
            "defaultLocale": "en",
            "supportedLocales": ["en", "ru"],
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
                "version": "2026-08-03",
                "modalTitle": {
                    "ru": "Согласие на обезличенную аналитику",
                    "en": "Consent for anonymous analytics",
                },
                "modalBodyMarkdown": {
                    "ru": "Сайт собирает только обезличенную агрегированную статистику просмотров, кликов и числа сессий. Данные не привязываются к IP, личности или постоянному идентификатору устройства.",
                    "en": "The site collects only anonymous aggregated statistics about views, clicks, and session counts. The data is not tied to IP, identity, or a permanent device identifier.",
                },
                "acceptButtonLabel": {
                    "ru": "Продолжить и согласиться",
                    "en": "Continue and agree",
                },
                "rejectButtonLabel": {
                    "ru": "Отказаться и закрыть сайт",
                    "en": "Decline and close site",
                },
            }
        },
        "seo": {
            "siteName": {
                "ru": "Портфолио Д. А. Куренкова",
                "en": "D. A. Kurenkov Portfolio",
            },
            "openGraphImage": "/rules/photo_2025-04-09_22-18-09.jpg",
        },
    }

    return deepcopy(payload)


class InMemoryContentRepository:
    """Возвращает опубликованный или черновой слепок до подключения реальной БД."""

    async def get_snapshot(self, snapshot_kind: str) -> PortfolioSnapshotRecord:
        """Отдаёт snapshot в формате, близком к будущему content_json."""

        normalized_snapshot_kind = "draft" if snapshot_kind == "draft" else "published"

        return PortfolioSnapshotRecord(
            snapshot_kind=normalized_snapshot_kind,
            content_schema_version="portfolio.v1",
            content_checksum_sha256="4bf7ef4df5c0bb36c877a53d40d7c11efca6259ac8e08a34b8d7756ab8c37b1f"
            if normalized_snapshot_kind == "draft"
            else "32f59f3f5c3167eb56f3fddb1fe2b8d65e4c2bf05fb957c756104dad43dff5c0",
            updated_at="2026-08-03T16:25:00Z"
            if normalized_snapshot_kind == "draft"
            else "2026-08-03T16:05:00Z",
            payload=build_preview_payload(normalized_snapshot_kind),
        )
