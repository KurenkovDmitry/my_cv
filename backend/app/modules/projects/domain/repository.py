"""Порты доступа к данным модуля projects."""

from typing import Protocol

from app.modules.projects.domain.entities import Project


class ProjectRepository(Protocol):
    """Контракт репозитория проектов."""

    async def list_featured(self) -> list[Project]:
        ...

