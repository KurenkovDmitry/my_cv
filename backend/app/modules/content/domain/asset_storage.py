"""Контракт управляемого хранилища файлов контента."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(slots=True, frozen=True)
class StoredContentAsset:
    """Описывает безопасно сохранённый файл, на который может ссылаться snapshot."""

    asset_id: str
    file_name: str
    media_type: str
    file_size_bytes: int
    checksum_sha256: str


class ContentAssetStorage(Protocol):
    """Изолирует application-слой от конкретной файловой системы или object storage."""

    async def write_asset(
        self,
        *,
        file_name: str,
        document_bytes: bytes,
        requested_media_type: str | None,
        preferred_asset_id: str | None = None,
    ) -> StoredContentAsset:
        """Проверяет и сохраняет файл, при импорте позволяя восстановить стабильный asset id."""

    async def get_asset(self, asset_id: str) -> StoredContentAsset:
        """Возвращает метаданные существующего файла."""

    async def list_assets(self) -> list[StoredContentAsset]:
        """Возвращает все управляемые файлы для административного реестра."""

    async def read_asset_bytes(self, asset_id: str) -> bytes:
        """Читает файл для backup bundle или публичной выдачи."""

    async def resolve_asset_path(self, asset_id: str) -> Path:
        """Возвращает нормализованный путь файла внутри разрешённого storage root."""

    async def delete_asset(self, asset_id: str) -> StoredContentAsset:
        """Удаляет управляемый файл и возвращает его последние метаданные."""
