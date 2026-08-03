"""Локальное file-backed storage для staged import candidate."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import Settings
from app.modules.system.domain.storage import ImportCandidateStorage, StoredBundleDocument


class LocalImportCandidateStorage(ImportCandidateStorage):
    """Сохраняет staged import candidate файлы в отдельной подпапке локального storage."""

    def __init__(self, settings: Settings) -> None:
        configured_root = Path(settings.backup_storage_path)
        base_root = configured_root if configured_root.is_absolute() else Path.cwd() / configured_root
        self._root_directory = base_root / "import-candidates"

    async def write_candidate_document(
        self,
        *,
        source_file_name: str,
        document_bytes: bytes,
    ) -> StoredBundleDocument:
        """Сохраняет загруженный import candidate документ как JSON-файл."""

        checksum_sha256 = hashlib.sha256(document_bytes).hexdigest()
        safe_source_stem = Path(source_file_name).stem or "import-candidate"

        timestamp = datetime.now(timezone.utc)
        relative_path = Path(timestamp.strftime("%Y")) / timestamp.strftime("%m") / (
            f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{safe_source_stem}-{uuid4().hex[:8]}.json"
        )
        absolute_path = await self._resolve_candidate_path(relative_path.as_posix())

        await asyncio.to_thread(absolute_path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(absolute_path.write_bytes, document_bytes)

        return StoredBundleDocument(
            storage_disk="local",
            storage_path=relative_path.as_posix(),
            file_name=absolute_path.name,
            file_size_bytes=len(document_bytes),
            checksum_sha256=checksum_sha256,
        )

    async def delete_candidate_document(self, storage_path: str) -> None:
        """Удаляет staged import candidate файл, если он ещё существует."""

        absolute_path = await self._resolve_candidate_path(storage_path)
        if not absolute_path.exists():
            return

        await asyncio.to_thread(absolute_path.unlink)

    async def load_candidate_document(self, storage_path: str) -> dict[str, Any]:
        """Загружает исходный JSON-документ staged import candidate."""

        absolute_path = await self._resolve_candidate_path(storage_path)
        document_bytes = await asyncio.to_thread(absolute_path.read_bytes)
        loaded_document = json.loads(document_bytes.decode("utf-8"))
        if not isinstance(loaded_document, dict):
            raise ValueError("Import candidate document must be a JSON object.")

        return dict(loaded_document)

    async def _resolve_candidate_path(self, storage_path: str) -> Path:
        """Возвращает нормализованный абсолютный путь внутри root staged import storage."""

        candidate_path = (self._root_directory / Path(storage_path)).resolve()
        root_directory = self._root_directory.resolve()

        if root_directory not in candidate_path.parents and candidate_path != root_directory:
            raise ValueError("Import candidate storage path is outside of configured root directory.")

        return candidate_path
