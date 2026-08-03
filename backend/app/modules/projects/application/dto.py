"""DTO приложения для модуля projects."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ProjectListItemDto:
    """DTO одной карточки проекта."""

    identifier: str
    slug: str
    title: str
    summary: str
    featured: bool
    technologies: tuple[str, ...]

