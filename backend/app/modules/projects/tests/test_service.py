"""Unit-тесты модуля projects."""

import pytest

from app.modules.projects.application.service import ProjectService
from app.modules.projects.infrastructure.postgres_repository import InMemoryProjectRepository


@pytest.mark.asyncio
async def test_project_service_returns_ru_title() -> None:
    """Проверяет, что локализованный заголовок выбирается по locale."""

    service = ProjectService(project_repository=InMemoryProjectRepository())

    project_items = await service.list_featured(locale_code="ru")

    assert project_items[0].title == "Платформа персонального портфолио"

