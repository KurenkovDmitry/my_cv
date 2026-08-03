"""Application-сервис snapshot-модуля контента."""

from app.modules.content.domain.entities import PortfolioSnapshotRecord
from app.modules.content.domain.repository import ContentRepository


class ContentService:
    """Оркестрирует чтение опубликованного и чернового snapshot без знания конкретного хранилища."""

    def __init__(self, content_repository: ContentRepository) -> None:
        self._content_repository = content_repository

    async def get_public_snapshot(self) -> PortfolioSnapshotRecord:
        """Возвращает опубликованный snapshot как единый документ для SSR-выдачи."""

        return await self._content_repository.get_snapshot(snapshot_kind="published")

    async def get_snapshot(self, snapshot_kind: str) -> PortfolioSnapshotRecord:
        """Возвращает snapshot нужного типа для public или admin-контура."""

        return await self._content_repository.get_snapshot(snapshot_kind=snapshot_kind)
