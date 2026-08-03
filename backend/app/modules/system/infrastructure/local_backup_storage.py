"""Локальное file-backed storage для backup/export bundle."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import Settings
from app.modules.system.domain.storage import BackupBundleStorage, StoredBundleDocument


class LocalBackupBundleStorage(BackupBundleStorage):
    """Сохраняет backup/export bundle в локальной файловой системе."""

    def __init__(self, settings: Settings) -> None:
        configured_root = Path(settings.backup_storage_path)
        self._root_directory = configured_root if configured_root.is_absolute() else Path.cwd() / configured_root

    async def write_bundle(
        self,
        *,
        snapshot_kind: str,
        backup_kind: str,
        bundle_payload: dict[str, object],
    ) -> StoredBundleDocument:
        """Сериализует bundle в JSON-файл и возвращает его метаданные."""

        bundle_bytes = json.dumps(
            bundle_payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        checksum_sha256 = hashlib.sha256(bundle_bytes).hexdigest()

        timestamp = datetime.now(timezone.utc)
        relative_path = Path(snapshot_kind) / timestamp.strftime("%Y") / timestamp.strftime("%m") / (
            f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{backup_kind}-{uuid4().hex[:8]}.bundle.json"
        )
        absolute_path = await self.resolve_bundle_path(relative_path.as_posix())

        await asyncio.to_thread(absolute_path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(absolute_path.write_bytes, bundle_bytes)

        return StoredBundleDocument(
            storage_disk="local",
            storage_path=relative_path.as_posix(),
            file_name=absolute_path.name,
            file_size_bytes=len(bundle_bytes),
            checksum_sha256=checksum_sha256,
        )

    async def delete_bundle(self, storage_path: str) -> None:
        """Удаляет bundle-файл, если он ещё существует в локальном storage."""

        absolute_path = await self.resolve_bundle_path(storage_path)
        if not absolute_path.exists():
            return

        await asyncio.to_thread(absolute_path.unlink)

    async def resolve_bundle_path(self, storage_path: str) -> Path:
        """Возвращает нормализованный абсолютный путь внутри разрешённого root."""

        candidate_path = (self._root_directory / Path(storage_path)).resolve()
        root_directory = self._root_directory.resolve()

        if root_directory not in candidate_path.parents and candidate_path != root_directory:
            raise ValueError("Backup storage path is outside of configured root directory.")

        return candidate_path

    async def load_bundle_document(self, storage_path: str) -> dict[str, Any]:
        """Загружает исходный JSON/bundle-документ для on-demand diff."""

        absolute_path = await self.resolve_bundle_path(storage_path)
        document_bytes = await asyncio.to_thread(absolute_path.read_bytes)
        loaded_document = json.loads(document_bytes.decode("utf-8"))
        if not isinstance(loaded_document, dict):
            raise ValueError("Backup bundle document must be a JSON object.")

        return dict(loaded_document)
