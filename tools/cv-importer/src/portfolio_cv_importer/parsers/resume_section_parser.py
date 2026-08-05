"""Разбор секций и склейка пунктов resume-like документов."""

from __future__ import annotations

from portfolio_cv_importer.domain.models import ResumeEntry, ResumeSections
from portfolio_cv_importer.normalizers.text_normalizer import PERIOD_PATTERN, normalize_extracted_line


def split_resume_sections(extracted_lines: list[str]) -> ResumeSections:
    """Разделяет общий поток строк на логические секции резюме."""

    education_heading_index = find_heading_index(extracted_lines, "ОСН. И ДОП. ОБРАЗОВАНИЕ", "Образование")
    experience_heading_index = find_heading_index(extracted_lines, "ОПЫТ РАБОТЫ", "Experience")
    skills_heading_index = find_heading_index(extracted_lines, "НАВЫКИ", "Skills")
    projects_heading_index = find_heading_index(extracted_lines, "ПРОЕКТЫ", "Projects")
    study_projects_heading_index = find_heading_index(extracted_lines, "УЧЕБНЫЕ ПРОЕКТЫ", "Study projects")

    contact_line = extracted_lines[2] if len(extracted_lines) > 2 else "Россия, Москва"

    return ResumeSections(
        location_ru=(contact_line.split("⋄")[0].strip() if "⋄" in contact_line else "Россия, Москва"),
        location_en="Moscow, Russia",
        education_lines=extract_section_lines(extracted_lines, education_heading_index, experience_heading_index),
        experience_lines=extract_section_lines(extracted_lines, experience_heading_index, skills_heading_index),
        project_lines=extract_section_lines(extracted_lines, projects_heading_index, study_projects_heading_index),
        study_project_lines=extract_section_lines(extracted_lines, study_projects_heading_index, len(extracted_lines)),
    )


def collect_bullet_entries(section_lines: list[str]) -> list[ResumeEntry]:
    """Склеивает многострочные bullet-пункты в компактные записи с периодом."""

    entries: list[ResumeEntry] = []
    current_text_lines: list[str] = []
    current_period = ""

    for raw_line in section_lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("•"):
            if current_text_lines:
                entries.append(
                    ResumeEntry(
                        text=normalize_extracted_line(" ".join(current_text_lines)),
                        period=normalize_extracted_line(current_period),
                    ),
                )

            current_text_lines = [line.removeprefix("•").strip()]
            current_period = ""
            continue

        if not current_text_lines:
            continue

        if PERIOD_PATTERN.search(line) and not current_period:
            current_period = line
            continue

        current_text_lines.append(line)

    if current_text_lines:
        entries.append(
            ResumeEntry(
                text=normalize_extracted_line(" ".join(current_text_lines)),
                period=normalize_extracted_line(current_period),
            ),
        )

    return entries


def find_heading_index(extracted_lines: list[str], *heading_variants: str) -> int:
    """Возвращает индекс заголовка секции или край списка, если заголовок не найден."""

    lowered_variants = [heading_variant.lower() for heading_variant in heading_variants]
    for line_index, line in enumerate(extracted_lines):
        lowered_line = line.lower()
        if any(heading_variant in lowered_line for heading_variant in lowered_variants):
            return line_index

    return len(extracted_lines)


def extract_section_lines(extracted_lines: list[str], start_index: int, end_index: int) -> list[str]:
    """Безопасно извлекает диапазон строк секции между двумя индексами."""

    if start_index >= len(extracted_lines):
        return []

    safe_start_index = min(start_index + 1, len(extracted_lines))
    safe_end_index = min(max(end_index, safe_start_index), len(extracted_lines))
    return extracted_lines[safe_start_index:safe_end_index]
