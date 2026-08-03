"""Доменные сущности служебного admin/system-контура."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class AdminContentStateRecord:
    """Служебное состояние админки и импорта."""

    state_key: str
    source_metadata: dict[str, Any]
    last_import_status: str
    last_imported_at: str | None
    pending_import_candidate_id: str | None
    current_backup_artifact_id: str | None
    updated_at: str


@dataclass(slots=True, frozen=True)
class BackupArtifactRecord:
    """Компактное представление backup/export-артефакта."""

    backup_id: str
    backup_kind: str
    snapshot_kind: str
    file_name: str
    storage_path: str
    checksum_sha256: str
    content_schema_version: str
    file_size_bytes: int
    created_at: str
    created_by_actor: str


@dataclass(slots=True, frozen=True)
class ImportCandidateRecord:
    """Компактное представление staged import-кандидата."""

    import_candidate_id: str
    parse_status: str
    content_schema_version: str
    storage_path: str
    checksum_sha256: str
    created_at: str
    created_by_actor: str
    review_summary: dict[str, Any]
