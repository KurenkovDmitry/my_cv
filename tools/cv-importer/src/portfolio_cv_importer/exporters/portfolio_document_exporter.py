"""Экспортеры нормализованного `portfolio.v1`."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from portfolio_cv_importer.domain.constants import (
    PORTFOLIO_BUNDLE_VERSION,
    PORTFOLIO_VERSION,
    RESUME_EXPORT_SECTION_TITLES,
)
from portfolio_cv_importer.errors import InvalidPortfolioDocumentError


def export_portfolio_json(payload: dict[str, object]) -> str:
    """Сериализует raw `portfolio.v1`."""

    validate_portfolio_payload(payload)
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def export_portfolio_bundle(payload: dict[str, object]) -> str:
    """Сериализует `portfolio.v1` в export/import bundle."""

    validate_portfolio_payload(payload)
    exported_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    bundle_payload = {
        "bundleVersion": PORTFOLIO_BUNDLE_VERSION,
        "exportedAt": exported_at,
        "backupKind": "manual_export",
        "snapshotKind": "draft",
        "snapshot": {
            "snapshotKind": "draft",
            "contentSchemaVersion": PORTFOLIO_VERSION,
            "contentChecksumSha256": "",
            "updatedAt": exported_at,
            "payload": payload,
        },
    }
    return json.dumps(bundle_payload, ensure_ascii=False, indent=2) + "\n"


def export_resume_markdown(payload: dict[str, object], locale_code: str = "ru") -> str:
    """Экспортирует `portfolio.v1` обратно в resume-like markdown."""

    validate_portfolio_payload(payload)
    profile = read_dict(payload, "profile")
    experience_items = read_list(payload, "experience")
    project_items = read_list(payload, "projects")
    education_items = read_list(payload, "education")
    focus_areas = read_list(read_dict(payload, "skills"), "focusAreas")

    lines = [
        f"# {read_localized_text(read_dict(profile, 'displayName'), locale_code)}",
        "",
        read_localized_text(read_dict(profile, "headline"), locale_code),
        "",
        f"## {RESUME_EXPORT_SECTION_TITLES['contacts'][locale_code]}",
        read_localized_text(read_dict(profile, "location"), locale_code),
        "",
        f"## {RESUME_EXPORT_SECTION_TITLES['summary'][locale_code]}",
        read_localized_text(read_dict(profile, "summary"), locale_code),
        "",
        f"## {RESUME_EXPORT_SECTION_TITLES['experience'][locale_code]}",
    ]

    for experience_item in experience_items:
        experience_item_dict = ensure_dict(experience_item)
        lines.append(
            f"- {read_localized_text(read_dict(experience_item_dict, 'company'), locale_code)}: "
            f"{read_localized_text(read_dict(experience_item_dict, 'role'), locale_code)}",
        )

    lines.extend(["", f"## {RESUME_EXPORT_SECTION_TITLES['projects'][locale_code]}"])
    for project_item in project_items:
        project_item_dict = ensure_dict(project_item)
        lines.append(
            f"- {read_localized_text(read_dict(project_item_dict, 'title'), locale_code)}: "
            f"{read_localized_text(read_dict(project_item_dict, 'summary'), locale_code)}",
        )

    lines.extend(["", f"## {RESUME_EXPORT_SECTION_TITLES['education'][locale_code]}"])
    for education_item in education_items:
        education_item_dict = ensure_dict(education_item)
        lines.append(f"- {read_localized_text(read_dict(education_item_dict, 'title'), locale_code)}")

    lines.extend(["", f"## {RESUME_EXPORT_SECTION_TITLES['skills'][locale_code]}"])
    for focus_area in focus_areas:
        if isinstance(focus_area, str):
            lines.append(f"- {focus_area}")

    return "\n".join(lines).strip() + "\n"


def validate_portfolio_payload(payload: dict[str, object]) -> None:
    """Проверяет минимальные признаки `portfolio.v1` перед экспортом."""

    if payload.get("version") != PORTFOLIO_VERSION:
        raise InvalidPortfolioDocumentError("Payload version must be 'portfolio.v1'.")

    if not isinstance(payload.get("profile"), dict):
        raise InvalidPortfolioDocumentError("Portfolio payload must contain a profile object.")


def read_localized_text(localized_block: dict[str, object], locale_code: str) -> str:
    """Читает локализованный текст из блока `{ru, en}`."""

    localized_value = localized_block.get(locale_code)
    if isinstance(localized_value, str) and localized_value:
        return localized_value

    fallback_value = localized_block.get("en")
    if isinstance(fallback_value, str) and fallback_value:
        return fallback_value

    fallback_value = localized_block.get("ru")
    return fallback_value if isinstance(fallback_value, str) else ""


def read_dict(payload: dict[str, object], key: str) -> dict[str, object]:
    """Возвращает словарь по ключу или пустой словарь."""

    value = payload.get(key)
    return ensure_dict(value)


def ensure_dict(value: object) -> dict[str, object]:
    """Безопасно приводит значение к словарю."""

    return value if isinstance(value, dict) else {}


def read_list(payload: dict[str, object], key: str) -> list[object]:
    """Возвращает список по ключу или пустой список."""

    value = payload.get(key)
    return value if isinstance(value, list) else []
