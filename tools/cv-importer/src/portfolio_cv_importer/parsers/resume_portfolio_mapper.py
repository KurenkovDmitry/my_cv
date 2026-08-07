"""Универсальный маппинг секций CV в `portfolio.v1`."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Iterable

from portfolio_cv_importer.domain.default_portfolio_factory import create_base_portfolio_payload
from portfolio_cv_importer.domain.models import ResumeEntry, ResumeSections
from portfolio_cv_importer.parsers.resume_section_parser import collect_bullet_entries


_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}")
_PHONE_PATTERN = re.compile(r"\+?\d[\d\s()-]{7,}\d")
_URL_PATTERN = re.compile(r"https?://[^\s)]+", re.IGNORECASE)
_CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
_SKILL_SEPARATOR_PATTERN = re.compile(r"[,;|•·]+")


def build_portfolio_payload_from_resume_sections(resume_sections: ResumeSections) -> dict[str, object]:
    """Собирает review-ready payload, сохраняя исходные формулировки документа."""

    display_name, headline = detect_profile_identity(resume_sections.header_lines)
    summary = " ".join(resume_sections.section_lines.get("summary", [])).strip() or headline
    portfolio_payload = create_base_portfolio_payload(
        display_name_ru=display_name,
        display_name_en=display_name,
        headline_ru=headline,
        headline_en=headline,
        location_ru=resume_sections.location_ru,
        location_en=resume_sections.location_en,
    )
    profile = portfolio_payload["profile"]
    if isinstance(profile, dict):
        profile["summary"] = localized_text(summary or "Требуется ручная проверка профиля")
        contacts = collect_contacts(resume_sections.header_lines)
        if contacts:
            profile["contacts"] = contacts

    portfolio_payload["education"] = collect_mapped_education_entries(resume_sections)
    portfolio_payload["experience"] = collect_mapped_experience_entries(resume_sections)
    portfolio_payload["projects"] = collect_mapped_project_entries(resume_sections)
    portfolio_payload["skills"] = collect_mapped_skills(resume_sections)
    portfolio_payload["localization"] = {
        "defaultLocale": "ru" if _CYRILLIC_PATTERN.search(" ".join(resume_sections.header_lines)) else "en",
        "supportedLocales": ["ru", "en"],
        "autoDetectByRegion": {"RU": "ru"},
    }
    portfolio_payload["seo"] = {"siteName": localized_text(display_name or "Imported CV")}
    portfolio_payload["importMetadata"] = {
        "detectedLayout": resume_sections.detected_layout,
        "detectedSections": sorted(resume_sections.section_lines),
    }
    return portfolio_payload


def collect_mapped_education_entries(resume_sections: ResumeSections) -> list[dict[str, object]]:
    """Преобразует образование без словаря конкретных вузов."""

    return [
        _map_education_entry(entry, entry_index)
        for entry_index, entry in enumerate(collect_bullet_entries(resume_sections.education_lines), start=1)
    ]


def collect_mapped_experience_entries(resume_sections: ResumeSections) -> list[dict[str, object]]:
    """Преобразует опыт в последовательность универсальных карточек."""

    return [
        _map_experience_entry(entry, entry_index)
        for entry_index, entry in enumerate(collect_bullet_entries(resume_sections.experience_lines), start=1)
    ]


def collect_mapped_project_entries(resume_sections: ResumeSections) -> list[dict[str, object]]:
    """Преобразует коммерческие, учебные и личные проекты без именных правил."""

    project_entries = collect_bullet_entries(
        [*resume_sections.project_lines, *resume_sections.study_project_lines],
    )
    return [_map_project_entry(entry, entry_index) for entry_index, entry in enumerate(project_entries, start=1)]


def collect_mapped_skills(resume_sections: ResumeSections) -> dict[str, object]:
    """Собирает группы компетенций и отдельные подтверждения навыков."""

    skill_groups: list[dict[str, object]] = []
    focus_areas: list[str] = []
    ungrouped_items: list[str] = []
    for line_index, line in enumerate(resume_sections.section_lines.get("skills", []), start=1):
        group_title, separator, raw_items = line.partition(":")
        if separator:
            items = _split_skill_items(raw_items)
            if items:
                skill_groups.append(
                    {
                        "id": build_stable_id("skill-group", group_title, line_index),
                        "title": localized_text(group_title.strip()),
                        "items": items,
                    },
                )
                focus_areas.extend(items)
            continue
        ungrouped_items.extend(_split_skill_items(line.removeprefix("•").strip()))

    if ungrouped_items:
        skill_groups.append(
            {
                "id": "skill-group-general",
                "title": localized_text("Ключевые навыки" if _contains_cyrillic(ungrouped_items) else "Key skills"),
                "items": _unique_strings(ungrouped_items),
            },
        )
        focus_areas.extend(ungrouped_items)

    proofs = [
        {
            "id": build_stable_id("proof", entry.text, proof_index),
            "skill": _first_nonempty(entry.lines, entry.text),
            "kind": "certificate",
            "title": localized_text(entry.text),
            **({"issuedAt": entry.period} if entry.period else {}),
        }
        for proof_index, entry in enumerate(
            collect_bullet_entries(resume_sections.section_lines.get("certifications", [])),
            start=1,
        )
    ]
    return {
        "focusAreas": _unique_strings(focus_areas)[:20],
        "groups": skill_groups,
        "proofs": proofs,
        "proofNote": localized_text("Данные импортированы из CV и требуют подтверждения перед публикацией."),
    }


def detect_profile_identity(header_lines: list[str]) -> tuple[str, str]:
    """Определяет имя и headline по верхнему блоку одноколоночных и двухколоночных CV."""

    candidate_lines = [line for line in header_lines if not _looks_like_contact(line)]
    display_name = next((line for line in candidate_lines if _looks_like_person_name(line)), "")
    headline = next(
        (
            line
            for line in candidate_lines
            if line != display_name and len(line) <= 180 and not _looks_like_location(line)
        ),
        "",
    )
    return display_name or "Имя не распознано", headline or "Профессиональный профиль требует проверки"


def collect_contacts(header_lines: list[str]) -> list[dict[str, str]]:
    """Извлекает email, телефон и публичные профили из header/sidebar блока."""

    contacts: list[dict[str, str]] = []
    seen_values: set[str] = set()
    for line in header_lines:
        for email in _EMAIL_PATTERN.findall(line):
            _append_contact(contacts, seen_values, "email", "Email", email, f"mailto:{email}")
        for phone in _PHONE_PATTERN.findall(line):
            normalized_phone = re.sub(r"[^\d+]", "", phone)
            _append_contact(contacts, seen_values, "phone", "Phone", phone.strip(), f"tel:{normalized_phone}")
        for url in _URL_PATTERN.findall(line):
            lowered_url = url.casefold()
            if "github.com" in lowered_url:
                kind, label = "github", "GitHub"
            elif "t.me" in lowered_url or "telegram" in lowered_url:
                kind, label = "telegram", "Telegram"
            else:
                kind, label = "social", "Profile"
            _append_contact(contacts, seen_values, kind, label, url, url)
    return contacts


def localized_text(value: str) -> dict[str, str]:
    """Не выдумывает перевод: обе локали получают исходный текст для последующей проверки."""

    normalized_value = value.strip()
    return {"ru": normalized_value, "en": normalized_value}


def build_stable_id(prefix: str, source_text: str, index: int) -> str:
    """Создаёт стабильный ASCII id из текста любого алфавита."""

    normalized_text = unicodedata.normalize("NFKD", source_text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_text.casefold()).strip("-")[:48]
    if not slug:
        slug = hashlib.sha1(source_text.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{slug}-{index}"


def _map_education_entry(entry: ResumeEntry, entry_index: int) -> dict[str, object]:
    title = _first_nonempty(entry.lines, entry.text)
    detail_lines = entry.lines[1:] if len(entry.lines) > 1 else []
    return {
        "id": build_stable_id("education", title, entry_index),
        "title": localized_text(title),
        **({"programme": localized_text(detail_lines[0])} if detail_lines else {}),
        **({"detail": localized_text(" ".join(detail_lines[1:]))} if len(detail_lines) > 1 else {}),
        **({"period": localized_text(entry.period)} if entry.period else {}),
        "status": "needs_review",
    }


def _map_experience_entry(entry: ResumeEntry, entry_index: int) -> dict[str, object]:
    company = _first_nonempty(entry.lines, entry.text)
    role = entry.lines[1] if len(entry.lines) > 1 else "Роль требует проверки"
    detail_lines = entry.lines[2:] if len(entry.lines) > 2 else []
    return {
        "id": build_stable_id("experience", company, entry_index),
        "company": localized_text(company),
        "role": localized_text(role),
        **({"period": localized_text(entry.period)} if entry.period else {}),
        **({"description": localized_text(entry.text)} if entry.text else {}),
        **({"highlights": [localized_text(line) for line in detail_lines]} if detail_lines else {}),
        "status": "needs_review",
    }


def _map_project_entry(entry: ResumeEntry, entry_index: int) -> dict[str, object]:
    title = _first_nonempty(entry.lines, entry.text)
    summary_lines = entry.lines[1:] if len(entry.lines) > 1 else [entry.text]
    summary = " ".join(line for line in summary_lines if line).strip() or title
    links = []
    for url in _URL_PATTERN.findall(entry.text):
        link_kind = "repository" if "github.com" in url.casefold() or "gitlab" in url.casefold() else "demo"
        links.append({"kind": link_kind, "label": localized_text("Ссылка"), "href": url})
    project_id = build_stable_id("project", title, entry_index)
    return {
        "id": project_id,
        "slug": project_id.removeprefix("project-"),
        "featured": entry_index <= 3,
        "status": "draft",
        "title": localized_text(title),
        "summary": localized_text(summary),
        **({"period": localized_text(entry.period)} if entry.period else {}),
        "technologies": _extract_technology_items(entry.lines),
        "links": links,
    }


def _extract_technology_items(lines: list[str]) -> list[str]:
    technology_labels = {"stack", "tech", "technologies", "technology", "стек", "технологии"}
    technology_lines = []
    for line in lines:
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        if label.strip().casefold() in technology_labels:
            technology_lines.append(value)
    return _unique_strings(item for line in technology_lines for item in _split_skill_items(line))


def _split_skill_items(value: str) -> list[str]:
    return [item.strip() for item in _SKILL_SEPARATOR_PATTERN.split(value) if item.strip()]


def _append_contact(
    contacts: list[dict[str, str]],
    seen_values: set[str],
    kind: str,
    label: str,
    value: str,
    href: str,
) -> None:
    if value in seen_values:
        return
    seen_values.add(value)
    contacts.append({"kind": kind, "label": label, "value": value, "href": href})


def _first_nonempty(lines: list[str], fallback: str) -> str:
    return next((line for line in lines if line.strip()), fallback).strip()


def _unique_strings(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        normalized_value = value.strip()
        comparison_key = normalized_value.casefold()
        if not normalized_value or comparison_key in seen_values:
            continue
        seen_values.add(comparison_key)
        result.append(normalized_value)
    return result


def _looks_like_contact(line: str) -> bool:
    return bool(_EMAIL_PATTERN.search(line) or _PHONE_PATTERN.search(line) or _URL_PATTERN.search(line))


def _looks_like_person_name(line: str) -> bool:
    if len(line) > 90 or any(character.isdigit() for character in line):
        return False
    words = [word.strip(".,|/") for word in line.split() if word.strip(".,|/")]
    if not 2 <= len(words) <= 6:
        return False
    return all(any(character.isalpha() for character in word) for word in words)


def _looks_like_location(line: str) -> bool:
    lowered_line = line.casefold()
    return "," in line or any(marker in lowered_line for marker in ("remote", "москва", "россия", "relocation"))


def _contains_cyrillic(values: Iterable[str]) -> bool:
    return _CYRILLIC_PATTERN.search(" ".join(values)) is not None
