"""Контракты file-backed storage для backup/export и import candidate bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True, frozen=True)
class StoredBundleDocument:
    """Метаданные уже сохранённого JSON/bundle-файла."""

    storage_disk: str
    storage_path: str
    file_name: str
    file_size_bytes: int
    checksum_sha256: str


class BackupBundleStorage(Protocol):
    """Фасад файлового хранилища backup/export bundle."""

    async def write_bundle(
        self,
        *,
        snapshot_kind: str,
        backup_kind: str,
        bundle_payload: dict[str, object],
    ) -> StoredBundleDocument:
        """Сохраняет export/import bundle и возвращает его компактные метаданные."""

    async def delete_bundle(self, storage_path: str) -> None:
        """Физически удаляет bundle-файл из хранилища."""

    async def resolve_bundle_path(self, storage_path: str) -> Path:
        """Возвращает абсолютный путь до bundle-файла для скачивания."""

    async def load_bundle_document(self, storage_path: str) -> dict[str, Any]:
        """Загружает исходный JSON/bundle-документ для on-demand diff."""


class ImportCandidateStorage(Protocol):
    """Фасад файлового хранилища staged import candidate."""

    async def write_candidate_document(
        self,
        *,
        source_file_name: str,
        document_bytes: bytes,
    ) -> StoredBundleDocument:
        """Сохраняет импортируемый документ и возвращает его метаданные."""

    async def delete_candidate_document(self, storage_path: str) -> None:
        """Физически удаляет staged import candidate файл."""

    async def load_candidate_document(self, storage_path: str) -> dict[str, Any]:
        """Загружает исходный staged import candidate JSON-документ."""
