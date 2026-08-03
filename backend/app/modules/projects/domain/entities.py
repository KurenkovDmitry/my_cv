"""Доменные сущности модуля projects."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Project:
    """Доменная сущность проекта."""

    identifier: str
    slug: str
    title_ru: str
    title_en: str
    summary_ru: str
    summary_en: str
    featured: bool
    technologies: tuple[str, ...]

