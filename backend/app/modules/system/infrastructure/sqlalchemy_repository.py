"""SQLAlchemy-репозитории служебного admin/system-контура."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.audit_models import AdminActionLog
from app.database.models.system_models import (
    AdminContentState,
    BackupArtifact,
    ImportCandidate,
    RuntimeHealthSnapshot,
)
from app.modules.system.domain.entities import (
    AdminContentStateRecord,
    BackupArtifactRecord,
    ImportCandidateRecord,
)
from app.modules.system.domain.repository import (
    BackupArtifactNotFoundError,
    ImportCandidateNotFoundError,
    SystemRepository,
    SystemStateNotFoundError,
)


def _serialize_datetime(value: datetime | None) -> str | None:
    """Нормализует nullable datetime в UTC ISO-формат, ожидаемый frontend-контрактами."""

    if value is None:
        return None

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class SqlAlchemySystemRepository:
    """Читает и изменяет служебные singleton/state-таблицы админки."""

    def __init__(self, database_session: AsyncSession) -> None:
        self._database_session = database_session

    async def get_admin_content_state(self) -> AdminContentStateRecord:
        """Возвращает системное состояние контентной админки по singleton-ключу."""

        state_select = select(AdminContentState).where(AdminContentState.state_key == "content_admin").limit(1)
        state_result = await self._database_session.execute(state_select)
        state_model = state_result.scalar_one_or_none()

        if state_model is None:
            raise SystemStateNotFoundError("Admin content state with key 'content_admin' is not available.")

        return self._map_admin_content_state_model(state_model=state_model)

    async def list_backup_artifacts(self) -> list[BackupArtifactRecord]:
        """Возвращает свежие backup/export-артефакты в формате, совместимом с админкой."""

        backup_select = select(BackupArtifact).order_by(BackupArtifact.created_at.desc()).limit(20)
        backup_result = await self._database_session.execute(backup_select)
        backup_models = backup_result.scalars().all()
        return [self._map_backup_artifact_model(backup_model) for backup_model in backup_models]

    async def get_backup_artifact(self, backup_id: str) -> BackupArtifactRecord:
        """Возвращает один backup-артефакт по идентификатору."""

        backup_model = await self._get_backup_artifact_model(backup_id=backup_id)
        return self._map_backup_artifact_model(backup_model)

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
        """Регистрирует новый backup/export bundle без немедленного commit."""

        backup_model = BackupArtifact(
            backup_kind=backup_kind,
            snapshot_kind=snapshot_kind,
            storage_disk=storage_disk,
            storage_path=storage_path,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            content_schema_version=content_schema_version,
            snapshot_checksum_sha256=snapshot_checksum_sha256,
            created_by_actor=created_by_actor,
            backup_metadata_json=backup_metadata,
        )
        self._database_session.add(backup_model)
        await self._database_session.flush()
        await self._database_session.refresh(backup_model)
        return self._map_backup_artifact_model(backup_model)

    async def delete_backup_artifact(self, backup_id: str) -> BackupArtifactRecord:
        """Удаляет backup-артефакт из registry и возвращает его метаданные."""

        backup_model = await self._get_backup_artifact_model(backup_id=backup_id)
        backup_record = self._map_backup_artifact_model(backup_model)
        await self._database_session.delete(backup_model)
        await self._database_session.flush()
        return backup_record

    async def list_import_candidates(self) -> list[ImportCandidateRecord]:
        """Возвращает staged import-кандидаты и review summary без загрузки тяжелых файлов."""

        import_candidate_select = select(ImportCandidate).order_by(ImportCandidate.created_at.desc()).limit(20)
        import_candidate_result = await self._database_session.execute(import_candidate_select)
        import_candidate_models = import_candidate_result.scalars().all()
        return [self._map_import_candidate_model(import_candidate_model) for import_candidate_model in import_candidate_models]

    async def get_import_candidate(self, import_candidate_id: str) -> ImportCandidateRecord:
        """Возвращает один staged import-кандидат по идентификатору."""

        import_candidate_model = await self._get_import_candidate_model(import_candidate_id=import_candidate_id)
        return self._map_import_candidate_model(import_candidate_model)

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
        """Регистрирует новый staged import candidate без немедленного commit."""

        import_candidate_model = ImportCandidate(
            storage_disk=storage_disk,
            storage_path=storage_path,
            checksum_sha256=checksum_sha256,
            content_schema_version=content_schema_version,
            parse_status=parse_status,
            created_by_actor=created_by_actor,
            review_summary_json=review_summary,
        )
        self._database_session.add(import_candidate_model)
        await self._database_session.flush()
        await self._database_session.refresh(import_candidate_model)
        return self._map_import_candidate_model(import_candidate_model)

    async def mark_pending_import_candidate(
        self,
        import_candidate_id: str,
        *,
        last_import_status: str,
        source_metadata_patch: dict[str, Any] | None = None,
    ) -> None:
        """Обновляет singleton-state активным staged import candidate."""

        state_model = await self._ensure_admin_content_state()
        state_model.pending_import_candidate_id = UUID(import_candidate_id)
        state_model.last_import_status = last_import_status
        state_model.updated_at = func.now()

        if source_metadata_patch:
            merged_source_metadata = dict(state_model.source_metadata_json)
            merged_source_metadata.update(source_metadata_patch)
            state_model.source_metadata_json = merged_source_metadata

        await self._database_session.flush()

    async def complete_import_review(
        self,
        *,
        last_import_status: str,
        last_imported_at: datetime,
        source_metadata_patch: dict[str, Any] | None = None,
    ) -> None:
        """Фиксирует завершение import-review и очищает pending candidate."""

        state_model = await self._ensure_admin_content_state()
        state_model.pending_import_candidate_id = None
        state_model.last_import_status = last_import_status
        state_model.last_imported_at = last_imported_at
        state_model.updated_at = func.now()

        if source_metadata_patch:
            merged_source_metadata = dict(state_model.source_metadata_json)
            merged_source_metadata.update(source_metadata_patch)
            state_model.source_metadata_json = merged_source_metadata

        await self._database_session.flush()

    async def update_current_backup_artifact(self, backup_id: str | None) -> None:
        """Обновляет singleton-state текущего backup для rollback-сценариев."""

        state_model = await self._ensure_admin_content_state()
        state_model.current_backup_artifact_id = UUID(backup_id) if backup_id else None
        state_model.updated_at = func.now()
        await self._database_session.flush()

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

        audit_log_model = AdminActionLog(
            occurred_at=occurred_at,
            actor_login=actor_login,
            action_code=action_code,
            entity_type=entity_type,
            entity_key=entity_key,
            result_code=result_code,
            request_id=request_id,
            change_summary_json=change_summary,
            metadata_json=metadata,
        )
        self._database_session.add(audit_log_model)
        await self._database_session.flush()

    async def get_runtime_health(self) -> dict[str, object]:
        """Возвращает текущий health snapshot для админки или сигнализирует, что он еще не заполнен."""

        health_select = select(RuntimeHealthSnapshot).where(RuntimeHealthSnapshot.snapshot_key == "current").limit(1)
        health_result = await self._database_session.execute(health_select)
        health_model = health_result.scalar_one_or_none()

        if health_model is None:
            raise SystemStateNotFoundError("Runtime health snapshot with key 'current' is not available.")

        health_snapshot = dict(health_model.health_json)
        health_snapshot.setdefault("sourceKind", health_model.source_kind)
        health_snapshot.setdefault("updatedAt", _serialize_datetime(health_model.updated_at) or "")
        return health_snapshot

    async def list_recent_audit_logs(self) -> list[dict[str, object]]:
        """Возвращает компактные audit-записи без хранения и отдачи тяжелых application logs."""

        audit_log_select = (
            select(AdminActionLog)
            .order_by(AdminActionLog.occurred_at.desc(), AdminActionLog.created_at.desc())
            .limit(20)
        )
        audit_log_result = await self._database_session.execute(audit_log_select)
        audit_log_models = audit_log_result.scalars().all()

        return [
            {
                "logId": str(audit_log_model.log_id),
                "occurredAt": _serialize_datetime(audit_log_model.occurred_at) or "",
                "actorLogin": audit_log_model.actor_login,
                "actionCode": audit_log_model.action_code,
                "entityType": audit_log_model.entity_type,
                "entityKey": audit_log_model.entity_key,
                "resultCode": audit_log_model.result_code,
            }
            for audit_log_model in audit_log_models
        ]

    async def _get_backup_artifact_model(self, backup_id: str) -> BackupArtifact:
        """Возвращает ORM-модель backup-артефакта или сигнализирует о его отсутствии."""

        try:
            normalized_backup_id = UUID(backup_id)
        except ValueError as error:
            raise BackupArtifactNotFoundError(f"Backup artifact '{backup_id}' is not available.") from error

        backup_select = select(BackupArtifact).where(BackupArtifact.backup_id == normalized_backup_id).limit(1)
        backup_result = await self._database_session.execute(backup_select)
        backup_model = backup_result.scalar_one_or_none()

        if backup_model is None:
            raise BackupArtifactNotFoundError(f"Backup artifact '{backup_id}' is not available.")

        return backup_model

    async def _get_import_candidate_model(self, import_candidate_id: str) -> ImportCandidate:
        """Возвращает ORM-модель staged import-кандидата или сигнализирует о его отсутствии."""

        try:
            normalized_import_candidate_id = UUID(import_candidate_id)
        except ValueError as error:
            raise ImportCandidateNotFoundError(
                f"Import candidate '{import_candidate_id}' is not available.",
            ) from error

        import_candidate_select = (
            select(ImportCandidate)
            .where(ImportCandidate.import_candidate_id == normalized_import_candidate_id)
            .limit(1)
        )
        import_candidate_result = await self._database_session.execute(import_candidate_select)
        import_candidate_model = import_candidate_result.scalar_one_or_none()

        if import_candidate_model is None:
            raise ImportCandidateNotFoundError(f"Import candidate '{import_candidate_id}' is not available.")

        return import_candidate_model

    async def _ensure_admin_content_state(self) -> AdminContentState:
        """Гарантирует наличие singleton-state для mutation-path операций."""

        state_select = select(AdminContentState).where(AdminContentState.state_key == "content_admin").limit(1)
        state_result = await self._database_session.execute(state_select)
        state_model = state_result.scalar_one_or_none()

        if state_model is not None:
            return state_model

        state_model = AdminContentState(
            state_key="content_admin",
            source_metadata_json={},
            last_import_status="idle",
        )
        self._database_session.add(state_model)
        await self._database_session.flush()
        return state_model

    def _map_admin_content_state_model(self, state_model: AdminContentState) -> AdminContentStateRecord:
        """Преобразует ORM-модель singleton-state в стабильную доменную сущность."""

        return AdminContentStateRecord(
            state_key=state_model.state_key,
            source_metadata=dict(state_model.source_metadata_json),
            last_import_status=state_model.last_import_status,
            last_imported_at=_serialize_datetime(state_model.last_imported_at),
            pending_import_candidate_id=(
                str(state_model.pending_import_candidate_id) if state_model.pending_import_candidate_id else None
            ),
            current_backup_artifact_id=(
                str(state_model.current_backup_artifact_id) if state_model.current_backup_artifact_id else None
            ),
            updated_at=_serialize_datetime(state_model.updated_at) or "",
        )

    def _map_backup_artifact_model(self, backup_model: BackupArtifact) -> BackupArtifactRecord:
        """Преобразует ORM-модель backup в компактную доменную сущность."""

        return BackupArtifactRecord(
            backup_id=str(backup_model.backup_id),
            backup_kind=backup_model.backup_kind,
            snapshot_kind=backup_model.snapshot_kind,
            file_name=Path(backup_model.storage_path).name,
            storage_path=backup_model.storage_path,
            checksum_sha256=backup_model.checksum_sha256,
            content_schema_version=backup_model.content_schema_version,
            file_size_bytes=backup_model.file_size_bytes,
            created_at=_serialize_datetime(backup_model.created_at) or "",
            created_by_actor=backup_model.created_by_actor or "system",
        )

    def _map_import_candidate_model(self, import_candidate_model: ImportCandidate) -> ImportCandidateRecord:
        """Преобразует ORM-модель staged import-кандидата в доменную сущность."""

        return ImportCandidateRecord(
            import_candidate_id=str(import_candidate_model.import_candidate_id),
            parse_status=import_candidate_model.parse_status,
            content_schema_version=import_candidate_model.content_schema_version,
            storage_path=import_candidate_model.storage_path,
            checksum_sha256=import_candidate_model.checksum_sha256,
            created_at=_serialize_datetime(import_candidate_model.created_at) or "",
            created_by_actor=import_candidate_model.created_by_actor or "system",
            review_summary=dict(import_candidate_model.review_summary_json),
        )


class FallbackSystemRepository:
    """Читает PostgreSQL, но сохраняет рабочий preview-режим, пока БД не заполнена или не поднята."""

    def __init__(
        self,
        primary_repository: SystemRepository,
        fallback_repository: SystemRepository,
    ) -> None:
        self._primary_repository = primary_repository
        self._fallback_repository = fallback_repository

    async def get_admin_content_state(self) -> AdminContentStateRecord:
        """Возвращает системное состояние из БД или preview-источника."""

        try:
            return await self._primary_repository.get_admin_content_state()
        except (SystemStateNotFoundError, SQLAlchemyError):
            return await self._fallback_repository.get_admin_content_state()

    async def list_backup_artifacts(self) -> list[BackupArtifactRecord]:
        """Возвращает backup registry из БД или fallback-источника."""

        try:
            return await self._primary_repository.list_backup_artifacts()
        except SQLAlchemyError:
            return await self._fallback_repository.list_backup_artifacts()

    async def get_backup_artifact(self, backup_id: str) -> BackupArtifactRecord:
        """Возвращает backup-артефакт из БД или fallback-источника."""

        try:
            return await self._primary_repository.get_backup_artifact(backup_id)
        except (BackupArtifactNotFoundError, SQLAlchemyError):
            return await self._fallback_repository.get_backup_artifact(backup_id)

    async def list_import_candidates(self) -> list[ImportCandidateRecord]:
        """Возвращает import-кандидаты из БД или fallback-источника."""

        try:
            return await self._primary_repository.list_import_candidates()
        except SQLAlchemyError:
            return await self._fallback_repository.list_import_candidates()

    async def get_import_candidate(self, import_candidate_id: str) -> ImportCandidateRecord:
        """Возвращает один staged import-кандидат из БД или fallback-источника."""

        try:
            return await self._primary_repository.get_import_candidate(import_candidate_id)
        except (ImportCandidateNotFoundError, SQLAlchemyError):
            return await self._fallback_repository.get_import_candidate(import_candidate_id)

    async def get_runtime_health(self) -> dict[str, object]:
        """Возвращает runtime health snapshot из БД или preview-источника."""

        try:
            return await self._primary_repository.get_runtime_health()
        except (SystemStateNotFoundError, SQLAlchemyError):
            return await self._fallback_repository.get_runtime_health()

    async def list_recent_audit_logs(self) -> list[dict[str, object]]:
        """Возвращает audit-лог из БД или preview-источника."""

        try:
            return await self._primary_repository.list_recent_audit_logs()
        except SQLAlchemyError:
            return await self._fallback_repository.list_recent_audit_logs()
