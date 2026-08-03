"""Контракты репозиториев snapshot-модуля контента."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.content.domain.entities import PortfolioSnapshotRecord


class ContentSnapshotNotFoundError(LookupError):
    """Сигнализирует, что в основном источнике пока нет нужного snapshot."""


class ContentRepository(Protocol):
    """Описывает минимальный контракт чтения контентного snapshot для SSR и админки."""

    async def get_snapshot(self, snapshot_kind: str) -> PortfolioSnapshotRecord:
        """Возвращает snapshot нужного типа из выбранного источника данных."""


class ContentMutationRepository(Protocol):
    """Контракт mutation-path для сохранения draft и публикации snapshot."""

    async def get_snapshot(self, snapshot_kind: str) -> PortfolioSnapshotRecord:
        """Возвращает snapshot нужного типа для дальнейшей мутации."""

    async def save_snapshot(
        self,
        snapshot_kind: str,
        payload: dict[str, object],
        content_schema_version: str,
        content_checksum_sha256: str,
        published_locale_codes: list[str],
        *,
        is_active: bool,
        published_at: datetime | None,
    ) -> PortfolioSnapshotRecord:
        """Создаёт или обновляет единый snapshot указанного типа."""


class ContentAdminRepository(ContentRepository, ContentMutationRepository, Protocol):
    """Объединённый контракт read+write для административного управления snapshot."""
