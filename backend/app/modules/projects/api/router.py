"""Router модуля projects."""

from fastapi import APIRouter, Query

from app.modules.projects.api.responses import ProjectListItemResponse, ProjectListResponse
from app.modules.projects.application.service import ProjectService
from app.modules.projects.infrastructure.postgres_repository import InMemoryProjectRepository

router = APIRouter(prefix="/projects", tags=["projects"])

project_service = ProjectService(project_repository=InMemoryProjectRepository())


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    locale: str = Query(default="en", pattern="^(ru|en)$"),
) -> ProjectListResponse:
    """Возвращает список featured-проектов для публичной витрины."""

    project_items = await project_service.list_featured(locale_code=locale)
    response_items = [
        ProjectListItemResponse(
            id=project_item.identifier,
            slug=project_item.slug,
            title=project_item.title,
            summary=project_item.summary,
            featured=project_item.featured,
            technologies=project_item.technologies,
        )
        for project_item in project_items
    ]
    return ProjectListResponse(items=response_items, total=len(response_items))

