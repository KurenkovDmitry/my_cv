"""Структурный разбор резюме без привязки к конкретному шаблону."""

from __future__ import annotations

import re

from portfolio_cv_importer.domain.models import ResumeEntry, ResumeSections
from portfolio_cv_importer.normalizers.text_normalizer import PERIOD_PATTERN, normalize_extracted_line


SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": (
        "about", "about me", "career objective", "objective", "profile", "professional profile",
        "professional summary", "summary", "обо мне", "о себе", "профиль", "профессиональный профиль", "цель",
    ),
    "experience": (
        "career history", "employment", "employment history", "experience", "professional experience",
        "work experience", "карьера", "опыт", "опыт работы", "профессиональный опыт", "трудовая деятельность",
    ),
    "education": (
        "academic background", "education", "education and training", "qualifications", "training",
        "образование", "основное и дополнительное образование", "осн и доп образование", "подготовка",
    ),
    "skills": (
        "competencies", "core competencies", "expertise", "key skills", "skills", "technical skills", "toolbox",
        "компетенции", "ключевые навыки", "навыки", "стек", "технологии", "экспертиза",
    ),
    "projects": (
        "academic projects", "key projects", "personal projects", "portfolio", "projects", "selected projects",
        "study projects", "избранные проекты", "портфолио", "проекты", "учебные проекты",
    ),
    "certifications": (
        "awards", "certificates", "certifications", "courses and certifications", "licenses and certifications",
        "professional development", "достижения", "курсы и сертификаты", "награды", "сертификаты",
        "сертификаты и рекомендации",
    ),
    "languages": ("languages", "языки", "иностранные языки"),
    "publications": ("publications", "research", "research and publications", "исследования", "публикации"),
    "volunteering": ("community", "volunteer experience", "volunteering", "волонтерство"),
}

_BULLET_PATTERN = re.compile(r"^[•●▪◦*-]\s*")
_NUMBERED_HEADING_PREFIX = re.compile(r"^(?:\d{1,2}|[ivx]{1,5})[.)\s/-]+", re.IGNORECASE)


def split_resume_sections(extracted_lines: list[str]) -> ResumeSections:
    """Выделяет семантические секции в chronological, functional и комбинированных CV."""

    normalized_lines = [normalize_extracted_line(line) for line in extracted_lines]
    normalized_lines = [line for line in normalized_lines if line]
    header_lines: list[str] = []
    section_lines: dict[str, list[str]] = {}
    current_section: str | None = None

    for line in normalized_lines:
        heading_match = classify_section_heading(line)
        if heading_match is not None:
            current_section, inline_content = heading_match
            section_lines.setdefault(current_section, [])
            if inline_content:
                section_lines[current_section].append(inline_content)
            continue

        if current_section is None:
            header_lines.append(line)
        else:
            section_lines.setdefault(current_section, []).append(line)

    location = detect_location(header_lines)
    project_lines = section_lines.get("projects", [])
    return ResumeSections(
        location_ru=location,
        location_en=location,
        education_lines=section_lines.get("education", []),
        experience_lines=section_lines.get("experience", []),
        project_lines=project_lines,
        study_project_lines=[],
        header_lines=header_lines,
        section_lines=section_lines,
        detected_layout=detect_resume_layout(normalized_lines, section_lines),
    )


def classify_section_heading(line: str) -> tuple[str, str] | None:
    """Распознаёт заголовок, включая нумерацию и вариант `Skills: Python, SQL`."""

    heading_source, separator, inline_content = line.partition(":")
    normalized_heading = _normalize_heading(heading_source if separator else line)
    for section_name, aliases in SECTION_ALIASES.items():
        if normalized_heading in aliases:
            return section_name, inline_content.strip() if separator else ""
    return None


def collect_bullet_entries(section_lines: list[str]) -> list[ResumeEntry]:
    """Собирает записи из bullet-, period-first и обычных текстовых секций."""

    normalized_lines = [normalize_extracted_line(line) for line in section_lines if line.strip()]
    if not normalized_lines:
        return []

    first_bullet_index = next((index for index, line in enumerate(normalized_lines) if _is_bullet(line)), None)
    first_period_index = next(
        (index for index, line in enumerate(normalized_lines) if PERIOD_PATTERN.search(line)),
        None,
    )
    if first_bullet_index is not None and (first_period_index is None or first_bullet_index <= first_period_index):
        return _collect_bullet_first_entries(normalized_lines)
    return _collect_period_first_entries(normalized_lines)


def find_heading_index(extracted_lines: list[str], *heading_variants: str) -> int:
    """Совместимый helper для клиентов прежней версии библиотеки."""

    normalized_variants = {_normalize_heading(variant) for variant in heading_variants}
    for line_index, line in enumerate(extracted_lines):
        if _normalize_heading(line) in normalized_variants:
            return line_index
    return len(extracted_lines)


def extract_section_lines(extracted_lines: list[str], start_index: int, end_index: int) -> list[str]:
    """Безопасно извлекает диапазон строк между двумя заголовками."""

    if start_index >= len(extracted_lines):
        return []
    safe_start_index = min(start_index + 1, len(extracted_lines))
    safe_end_index = min(max(end_index, safe_start_index), len(extracted_lines))
    return extracted_lines[safe_start_index:safe_end_index]


def detect_location(header_lines: list[str]) -> str:
    """Ищет строку локации среди контактов, не подставляя данные конкретного человека."""

    location_markers = ("remote", "relocation", "гибрид", "москва", "россия", "санкт-петербург", "удаленно")
    for line in header_lines:
        lowered_line = line.casefold()
        location_fragment = line.split("⋄", 1)[0].strip()
        if any(marker in location_fragment.casefold() for marker in location_markers):
            return location_fragment
        if "@" in line or "http" in lowered_line or re.search(r"\+?\d[\d\s()-]{7,}", line):
            continue
        has_location_marker = any(marker in lowered_line for marker in location_markers)
        looks_like_city_country = "," in line and not re.search(r"\d{4}", line)
        if has_location_marker or looks_like_city_country:
            return line.split("⋄", 1)[0].strip()
    return ""


def detect_resume_layout(normalized_lines: list[str], section_lines: dict[str, list[str]]) -> str:
    """Классифицирует распространённые семейства CV для diagnostics и review."""

    section_order = [
        heading[0]
        for line in normalized_lines
        if (heading := classify_section_heading(line)) is not None
    ]
    if "publications" in section_lines:
        return "academic"
    if "skills" in section_order and "experience" in section_order:
        return "functional" if section_order.index("skills") < section_order.index("experience") else "combination"
    if "experience" in section_lines:
        return "chronological"
    if sum(" | " in line or "\t" in line for line in normalized_lines) >= 3:
        return "two_column"
    return "unstructured"


def _collect_bullet_first_entries(lines: list[str]) -> list[ResumeEntry]:
    entries: list[ResumeEntry] = []
    current_lines: list[str] = []
    current_period = ""
    for line in lines:
        if _is_bullet(line):
            if current_lines:
                entries.append(_build_entry(current_lines, current_period))
            current_lines = [_strip_bullet(line)]
            current_period = ""
            continue
        if not current_lines:
            current_lines = [line]
            continue
        if PERIOD_PATTERN.search(line) and not current_period:
            current_period = line
        else:
            current_lines.append(line)
    if current_lines:
        entries.append(_build_entry(current_lines, current_period))
    return entries


def _collect_period_first_entries(lines: list[str]) -> list[ResumeEntry]:
    entries: list[ResumeEntry] = []
    current_lines: list[str] = []
    current_period = ""
    seen_detail_bullet = False

    for line_index, line in enumerate(lines):
        is_bullet = _is_bullet(line)
        upcoming_lines = lines[line_index + 1:line_index + 4]
        starts_next_entry = (
            current_period
            and seen_detail_bullet
            and not is_bullet
            and not PERIOD_PATTERN.search(line)
            and any(PERIOD_PATTERN.search(upcoming_line) for upcoming_line in upcoming_lines)
        )
        if starts_next_entry:
            entries.append(_build_entry(current_lines, current_period))
            current_lines = [line]
            current_period = ""
            seen_detail_bullet = False
            continue
        if PERIOD_PATTERN.search(line):
            if current_period:
                entries.append(_build_entry(current_lines, current_period))
                current_lines = []
            current_period = line
            continue
        current_lines.append(_strip_bullet(line))
        seen_detail_bullet = seen_detail_bullet or is_bullet

    if current_lines or current_period:
        entries.append(_build_entry(current_lines, current_period))
    return [entry for entry in entries if entry.text or entry.period]


def _build_entry(lines: list[str], period: str) -> ResumeEntry:
    clean_lines = [line.strip() for line in lines if line.strip()]
    return ResumeEntry(
        text=normalize_extracted_line(" ".join(clean_lines)),
        period=normalize_extracted_line(period),
        lines=clean_lines,
    )


def _normalize_heading(line: str) -> str:
    normalized = _NUMBERED_HEADING_PREFIX.sub("", line.strip().casefold())
    normalized = re.sub(r"[\s:|/\\._-]+", " ", normalized)
    return normalized.strip()


def _is_bullet(line: str) -> bool:
    return _BULLET_PATTERN.match(line) is not None


def _strip_bullet(line: str) -> str:
    return _BULLET_PATTERN.sub("", line).strip()
