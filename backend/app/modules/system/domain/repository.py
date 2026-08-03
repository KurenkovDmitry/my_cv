"""Контракты репозиториев служебного admin/system-контура."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.modules.system.domain.entities import (
    AdminContentStateRecord,
    BackupArtifactRecord,
    ImportCandidateRecord,
)


class SystemStateNotFoundError(LookupError):
    """Сигнализирует, что обязательный singleton-state пока не найден в БД."""


class BackupArtifactNotFoundError(LookupError):
    """Сигнализирует, что backup-артефакт не найден в registry."""


class ImportCandidateNotFoundError(LookupError):
    """Сигнализирует, что staged import candidate не найден."""


class SystemRepository(Protocol):
    """Описывает минимальный read-контракт служебных сущностей админки."""

    async def get_admin_content_state(self) -> AdminContentStateRecord:
        """Возвращает singleton-state контентного административного контура."""

    async def list_backup_artifacts(self) -> list[BackupArtifactRecord]:
        """Возвращает registry backup/export-файлов для админки."""

    async def get_backup_artifact(self, backup_id: str) -> BackupArtifactRecord:
        """Возвращает один backup-артефакт по идентификатору."""

    async def list_import_candidates(self) -> list[ImportCandidateRecord]:
        """Возвращает staged import-кандидаты для control version workflow."""

    async def get_import_candidate(self, import_candidate_id: str) -> ImportCandidateRecord:
        """Возвращает один staged import-кандидат по идентификатору."""

    async def get_runtime_health(self) -> dict[str, object]:
        """Возвращает компактный health snapshot без прямой привязки к Grafana."""

    async def list_recent_audit_logs(self) -> list[dict[str, object]]:
        """Возвращает последние записи audit-журнала админки."""


class SystemMutationRepository(Protocol):
    """Контракт mutation-path для backup registry, import candidate и audit log."""

    async def list_backup_artifacts(self) -> list[BackupArtifactRecord]:
        """Возвращает список backup-артефактов после мутаций."""

    async def get_backup_artifact(self, backup_id: str) -> BackupArtifactRecord:
        """Возвращает один backup-артефакт по идентификатору."""

    async def create_backup_artifact(
        self,
        *,
        backup_kind: str,
        snapshot_kind: str,
        storage_disk: str,
        storage_path: str,
        file_size_bytes: int,
        checksum_sha256: str,
        content_schema_version: str,
        snapshot_checksum_sha256: str,
        created_by_actor: str,
        backup_metadata: dict[str, object],
    ) -> BackupArtifactRecord:
        """Регистрирует новый backup/export bundle в PostgreSQL."""

    async def delete_backup_artifact(self, backup_id: str) -> BackupArtifactRecord:
        """Удаляет backup-артефакт из registry и возвращает его метаданные."""

    async def list_import_candidates(self) -> list[ImportCandidateRecord]:
        """Возвращает staged import-кандидаты после мутаций."""

    async def get_import_candidate(self, import_candidate_id: str) -> ImportCandidateRecord:
        """Возвращает один staged import-кандидат."""

    async def create_import_candidate(
        self,
        *,
        storage_disk: str,
        storage_path: str,
        checksum_sha256: str,
        content_schema_version: str,
        parse_status: str,
        created_by_actor: str,
        review_summary: dict[str, object],
    ) -> ImportCandidateRecord:
        """Регистрирует новый staged import candidate в PostgreSQL."""

    async def mark_pending_import_candidate(
        self,
        import_candidate_id: str,
        *,
        last_import_status: str,
        source_metadata_patch: dict[str, Any] | None = None,
    ) -> None:
        """Обновляет singleton-state активным staged import candidate."""

    async def complete_import_review(
        self,
        *,
        last_import_status: str,
        last_imported_at: datetime,
        source_metadata_patch: dict[str, Any] | None = None,
    ) -> None:
        """Фиксирует завершение import-review, очищает pending candidate и обновляет service-state."""

    async def update_current_backup_artifact(self, backup_id: str | None) -> None:
        """Обновляет singleton-state текущего backup для быстрых rollback-сценариев."""

    async def append_audit_log(
        self,
        *,
        occurred_at: datetime,
        actor_login: str,
        action_code: str,
        entity_type: str,
        entity_key: str | None,
        result_code: str,
        request_id: str | None,
        change_summary: dict[str, object] | None,
        metadata: dict[str, object] | None,
    ) -> None:
        """Пишет компактную audit-запись действия админки."""


class SystemAdminRepository(SystemRepository, SystemMutationRepository, Protocol):
    """Объединённый контракт read+write для административных системных операций."""
