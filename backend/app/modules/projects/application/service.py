"""Application-сервис модуля projects."""

from app.modules.projects.application.dto import ProjectListItemDto
from app.modules.projects.domain.repository import ProjectRepository


class ProjectService:
    """Оркестрирует чтение списка проектов без знания инфраструктурных деталей."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    async def list_featured(self, locale_code: str) -> list[ProjectListItemDto]:
        """Возвращает локализованный список featured-проектов."""

        projects = await self._project_repository.list_featured()
        project_items: list[ProjectListItemDto] = []

        for project in projects:
            project_items.append(
                ProjectListItemDto(
                    identifier=project.identifier,
                    slug=project.slug,
                    title=project.title_ru if locale_code == "ru" else project.title_en,
                    summary=project.summary_ru if locale_code == "ru" else project.summary_en,
                    featured=project.featured,
                    technologies=project.technologies,
                )
            )

        return project_items

