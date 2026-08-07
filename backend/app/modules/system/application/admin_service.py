"""Application-сервис mutation-path служебного admin/system-контура."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.application.asset_bundle import (
    build_asset_bundle_entries,
    collect_referenced_asset_ids,
    extract_bundled_assets,
    restore_bundled_assets,
)
from app.modules.content.domain.asset_storage import ContentAssetStorage
from app.modules.content.domain.entities import PortfolioSnapshotRecord
from app.modules.content.domain.repository import ContentAdminRepository
from app.modules.system.application.bundle_payloads import extract_portfolio_payload
from app.modules.system.application.import_field_review import (
    apply_import_field_patches,
    build_import_field_review,
)
from app.modules.system.application.resume_import_converter import ResumeImportConverter
from app.modules.system.domain.entities import BackupArtifactRecord, ImportCandidateRecord
from app.modules.system.domain.repository import SystemAdminRepository
from app.modules.system.domain.storage import BackupBundleStorage, ImportCandidateStorage


class SystemAdminService:
    """Оркестрирует backup/download/delete и staged import workflow админки."""

    def __init__(
        self,
        database_session: AsyncSession,
        content_repository: ContentAdminRepository,
        system_repository: SystemAdminRepository,
        backup_storage: BackupBundleStorage,
        import_candidate_storage: ImportCandidateStorage,
        resume_import_converter: ResumeImportConverter,
        asset_storage: ContentAssetStorage,
    ) -> None:
        self._database_session = database_session
        self._content_repository = content_repository
        self._system_repository = system_repository
        self._backup_storage = backup_storage
        self._import_candidate_storage = import_candidate_storage
        self._resume_import_converter = resume_import_converter
        self._asset_storage = asset_storage

    async def create_backup_artifact(
        self,
        *,
        snapshot_kind: str,
        backup_kind: str,
        actor_login: str,
        request_id: str | None,
    ) -> BackupArtifactRecord:
        """Создаёт новый file-backed backup по выбранному snapshot."""

        occurred_at = datetime.now(timezone.utc)
        created_backup: BackupArtifactRecord | None = None

        try:
            snapshot_record = await self._content_repository.get_snapshot(snapshot_kind=snapshot_kind)
            created_backup = await self._create_backup_from_snapshot_record(
                snapshot_record=snapshot_record,
                backup_kind=backup_kind,
                registry_snapshot_kind=snapshot_kind,
                actor_login=actor_login,
            )
            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="create_backup",
                entity_type="backup_artifact",
                entity_key=created_backup.backup_id,
                result_code="success",
                request_id=request_id,
                change_summary={
                    "snapshotKind": snapshot_kind,
                    "snapshotChecksumSha256": snapshot_record.content_checksum_sha256,
                    "backupChecksumSha256": created_backup.checksum_sha256,
                },
                metadata={
                    "backupKind": backup_kind,
                    "fileName": created_backup.file_name,
                },
            )
            await self._database_session.commit()
            return created_backup
        except Exception:
            await self._database_session.rollback()
            if created_backup is not None:
                await self._backup_storage.delete_bundle(created_backup.storage_path)
            raise

    async def delete_backup_artifact(
        self,
        *,
        backup_id: str,
        actor_login: str,
        request_id: str | None,
    ) -> BackupArtifactRecord:
        """Удаляет backup из registry и физически удаляет соответствующий bundle-файл."""

        occurred_at = datetime.now(timezone.utc)
        deleted_backup = await self._system_repository.get_backup_artifact(backup_id=backup_id)

        try:
            await self._backup_storage.delete_bundle(deleted_backup.storage_path)
            deleted_backup = await self._system_repository.delete_backup_artifact(backup_id=backup_id)

            current_state = await self._system_repository.get_admin_content_state()
            if current_state.current_backup_artifact_id == backup_id:
                await self._system_repository.update_current_backup_artifact(None)

            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="delete_backup",
                entity_type="backup_artifact",
                entity_key=deleted_backup.backup_id,
                result_code="success",
                request_id=request_id,
                change_summary={
                    "storagePath": deleted_backup.storage_path,
                    "fileName": deleted_backup.file_name,
                },
                metadata=None,
            )
            await self._database_session.commit()
            return deleted_backup
        except Exception:
            await self._database_session.rollback()
            raise

    async def resolve_backup_download_path(self, backup_id: str) -> Path:
        """Возвращает абсолютный путь к backup bundle для скачивания."""

        backup_record = await self._system_repository.get_backup_artifact(backup_id=backup_id)
        return await self._backup_storage.resolve_bundle_path(backup_record.storage_path)

    async def create_import_candidate(
        self,
        *,
        source_file_name: str,
        document_bytes: bytes,
        actor_login: str,
        request_id: str | None,
    ) -> ImportCandidateRecord:
        """Загружает file-backed import candidate и регистрирует его в БД."""

        occurred_at = datetime.now(timezone.utc)
        stored_candidate_document = None

        try:
            candidate_payload, source_type, bundled_assets = (
                await self._resume_import_converter.convert_to_portfolio_payload(
                    source_file_name=source_file_name,
                    document_bytes=document_bytes,
                )
            )
            review_summary = _build_review_summary(
                candidate_payload,
                source_type=source_type,
                source_file_name=source_file_name,
            )
            warning_messages = _build_warning_messages(candidate_payload)
            parse_status = "warning" if warning_messages else "parsed"
            normalized_candidate_document = {
                "bundleVersion": "portfolio.bundle.v2",
                "snapshot": {"payload": candidate_payload},
                "assets": bundled_assets,
            }
            normalized_candidate_document_bytes = json.dumps(
                normalized_candidate_document,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ).encode("utf-8")
            normalized_candidate_file_name = _build_normalized_candidate_file_name(source_file_name)

            stored_candidate_document = await self._import_candidate_storage.write_candidate_document(
                source_file_name=normalized_candidate_file_name,
                document_bytes=normalized_candidate_document_bytes,
            )
            created_import_candidate = await self._system_repository.create_import_candidate(
                storage_disk=stored_candidate_document.storage_disk,
                storage_path=stored_candidate_document.storage_path,
                checksum_sha256=stored_candidate_document.checksum_sha256,
                content_schema_version=_extract_content_schema_version(candidate_payload),
                parse_status=parse_status,
                created_by_actor=actor_login,
                review_summary=review_summary,
            )
            await self._system_repository.mark_pending_import_candidate(
                created_import_candidate.import_candidate_id,
                last_import_status=parse_status,
                source_metadata_patch={
                    "lastSourceType": source_type,
                    "lastSourceFilename": source_file_name,
                    "normalizedCandidateFileName": normalized_candidate_file_name,
                    "warnings": warning_messages,
                },
            )
            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="create_import_candidate",
                entity_type="import_candidate",
                entity_key=created_import_candidate.import_candidate_id,
                result_code=parse_status,
                request_id=request_id,
                change_summary={
                    "fileName": source_file_name,
                    "replaceableSections": review_summary["replaceableSections"],
                },
                metadata={
                    "checksumSha256": created_import_candidate.checksum_sha256,
                    "contentSchemaVersion": created_import_candidate.content_schema_version,
                    "sourceType": source_type,
                },
            )
            await self._database_session.commit()
            return created_import_candidate
        except Exception:
            await self._database_session.rollback()
            if stored_candidate_document is not None:
                await self._import_candidate_storage.delete_candidate_document(stored_candidate_document.storage_path)
            raise

    async def apply_import_candidate_to_draft(
        self,
        *,
        import_candidate_id: str,
        replace_mode: str,
        sections: list[str] | None,
        fields: list[dict[str, object]] | None,
        actor_login: str,
        request_id: str | None,
    ) -> tuple[PortfolioSnapshotRecord, BackupArtifactRecord | None, ImportCandidateRecord, list[str], list[str], str]:
        """Применяет candidate целиком, по разделам или по выбранным полям."""

        occurred_at = datetime.now(timezone.utc)
        created_backup: BackupArtifactRecord | None = None

        import_candidate_record = await self._system_repository.get_import_candidate(
            import_candidate_id=import_candidate_id,
        )
        candidate_document = await self._import_candidate_storage.load_candidate_document(
            import_candidate_record.storage_path,
        )
        candidate_payload = extract_portfolio_payload(candidate_document)
        bundled_assets = extract_bundled_assets(candidate_document)
        current_draft_snapshot = await self._content_repository.get_snapshot(snapshot_kind="draft")

        replaceable_sections = _pick_string_list(import_candidate_record.review_summary.get("replaceableSections"))
        applied_fields: list[str] = []
        if replace_mode == "field_replace":
            next_draft_payload, applied_fields = apply_import_field_patches(
                current_draft_snapshot.payload,
                candidate_payload,
                fields or [],
            )
            applied_sections = sorted({path.removeprefix("/").split("/", 1)[0] for path in applied_fields})
        else:
            applied_sections = _resolve_applied_sections(
                replace_mode=replace_mode,
                replaceable_sections=replaceable_sections,
                requested_sections=sections or [],
            )
            next_draft_payload = _build_next_draft_payload(
                replace_mode=replace_mode,
                current_payload=current_draft_snapshot.payload,
                candidate_payload=candidate_payload,
                applied_sections=applied_sections,
            )

        next_draft_payload["version"] = _extract_content_schema_version(candidate_payload)
        next_draft_payload["draft"] = True
        current_requires_review = bool(current_draft_snapshot.payload.get("needsManualReview"))
        candidate_requires_review = bool(candidate_payload.get("needsManualReview"))
        next_draft_payload["needsManualReview"] = current_requires_review or candidate_requires_review
        required_asset_ids = set(collect_referenced_asset_ids(next_draft_payload))
        applicable_bundled_assets = [
            asset_entry
            for asset_entry in bundled_assets
            if asset_entry.get("assetId") in required_asset_ids
        ]
        import_status = "applied_full" if replace_mode == "full_replace" else "applied_partial"
        warning_messages = _build_warning_messages(candidate_payload)
        source_type = import_candidate_record.review_summary.get("sourceType")
        source_file_name = import_candidate_record.review_summary.get("sourceFileName")
        restored_asset_ids: list[str] = []

        try:
            created_backup = await self._create_backup_from_snapshot_record(
                snapshot_record=current_draft_snapshot,
                backup_kind="pre_replace_backup",
                registry_snapshot_kind="before_replace",
                actor_login=actor_login,
            )
            restored_asset_ids = await restore_bundled_assets(
                applicable_bundled_assets,
                self._asset_storage,
            )
            saved_snapshot = await self._content_repository.save_snapshot(
                snapshot_kind="draft",
                payload=next_draft_payload,
                content_schema_version=_extract_content_schema_version(next_draft_payload),
                content_checksum_sha256=_build_content_checksum(next_draft_payload),
                published_locale_codes=_extract_published_locale_codes(next_draft_payload),
                is_active=True,
                published_at=None,
            )
            await self._system_repository.complete_import_review(
                last_import_status=import_status,
                last_imported_at=occurred_at,
                source_metadata_patch={
                    "lastSourceType": source_type if isinstance(source_type, str) and source_type else "import_bundle",
                    "lastSourceFilename": (
                        source_file_name
                        if isinstance(source_file_name, str) and source_file_name
                        else Path(import_candidate_record.storage_path).name
                    ),
                    "lastAppliedImportCandidateId": import_candidate_id,
                    "manualOverrides": [] if replace_mode == "full_replace" else (applied_fields or applied_sections),
                    "warnings": warning_messages,
                },
            )
            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="apply_import_candidate",
                entity_type="import_candidate",
                entity_key=import_candidate_id,
                result_code=import_status,
                request_id=request_id,
                change_summary={
                    "replaceMode": replace_mode,
                    "appliedSections": applied_sections,
                    "appliedFields": applied_fields,
                    "draftChecksumSha256": saved_snapshot.content_checksum_sha256,
                },
                metadata={
                    "backupArtifactId": created_backup.backup_id if created_backup else None,
                    "candidateChecksumSha256": import_candidate_record.checksum_sha256,
                },
            )
            await self._database_session.commit()
            return (
                saved_snapshot,
                created_backup,
                import_candidate_record,
                applied_sections,
                applied_fields,
                replace_mode,
            )
        except Exception:
            await self._database_session.rollback()
            if created_backup is not None:
                await self._backup_storage.delete_bundle(created_backup.storage_path)
            for restored_asset_id in restored_asset_ids:
                await self._asset_storage.delete_asset(restored_asset_id)
            raise

    async def get_import_candidate_field_review(
        self,
        *,
        import_candidate_id: str,
    ) -> tuple[ImportCandidateRecord, list[dict[str, object]]]:
        """Возвращает актуальный полевой diff candidate относительно текущего draft."""

        import_candidate_record = await self._system_repository.get_import_candidate(
            import_candidate_id=import_candidate_id,
        )
        candidate_document = await self._import_candidate_storage.load_candidate_document(
            import_candidate_record.storage_path,
        )
        candidate_payload = extract_portfolio_payload(candidate_document)
        current_draft_snapshot = await self._content_repository.get_snapshot(snapshot_kind="draft")
        return import_candidate_record, build_import_field_review(current_draft_snapshot.payload, candidate_payload)

    async def _create_backup_from_snapshot_record(
        self,
        *,
        snapshot_record: PortfolioSnapshotRecord,
        backup_kind: str,
        registry_snapshot_kind: str,
        actor_login: str,
    ) -> BackupArtifactRecord:
        """Создаёт backup по уже загруженному snapshot без хранения полного payload в БД."""

        exported_at = datetime.now(timezone.utc)
        bundled_assets = await build_asset_bundle_entries(
            snapshot_record.payload,
            self._asset_storage,
        )
        bundle_payload = {
            "bundleVersion": "portfolio.bundle.v2",
            "exportedAt": exported_at.isoformat().replace("+00:00", "Z"),
            "backupKind": backup_kind,
            "snapshotKind": registry_snapshot_kind,
            "snapshot": {
                "snapshotKind": snapshot_record.snapshot_kind,
                "contentSchemaVersion": snapshot_record.content_schema_version,
                "contentChecksumSha256": snapshot_record.content_checksum_sha256,
                "updatedAt": snapshot_record.updated_at,
                "payload": snapshot_record.payload,
            },
            "assets": bundled_assets,
        }
        stored_bundle = await self._backup_storage.write_bundle(
            snapshot_kind=registry_snapshot_kind,
            backup_kind=backup_kind,
            bundle_payload=bundle_payload,
        )

        try:
            backup_record = await self._system_repository.create_backup_artifact(
                backup_kind=backup_kind,
                snapshot_kind=registry_snapshot_kind,
                storage_disk=stored_bundle.storage_disk,
                storage_path=stored_bundle.storage_path,
                file_size_bytes=stored_bundle.file_size_bytes,
                checksum_sha256=stored_bundle.checksum_sha256,
                content_schema_version=snapshot_record.content_schema_version,
                snapshot_checksum_sha256=snapshot_record.content_checksum_sha256,
                created_by_actor=actor_login,
                backup_metadata={
                    "fileName": stored_bundle.file_name,
                    "exportedAt": bundle_payload["exportedAt"],
                    "bundleVersion": bundle_payload["bundleVersion"],
                },
            )
            await self._system_repository.update_current_backup_artifact(backup_record.backup_id)
            return backup_record
        except Exception:
            await self._backup_storage.delete_bundle(stored_bundle.storage_path)
            raise


def _build_content_checksum(payload: dict[str, object]) -> str:
    """Строит стабильную контрольную сумму snapshot payload."""

    normalized_payload = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(normalized_payload).hexdigest()


def _extract_content_schema_version(payload: dict[str, object]) -> str:
    """Извлекает версию контентной схемы из payload или возвращает безопасный default."""

    version = payload.get("version")
    return version if isinstance(version, str) and version else "portfolio.v1"


def _extract_published_locale_codes(payload: dict[str, object]) -> list[str]:
    """Извлекает список опубликованных локалей без лишних join или подтаблиц."""

    localization_block = payload.get("localization")
    if not isinstance(localization_block, dict):
        return []

    supported_locales = localization_block.get("supportedLocales")
    if not isinstance(supported_locales, list):
        return []

    return [locale_code for locale_code in supported_locales if isinstance(locale_code, str)]


def _build_warning_messages(candidate_payload: dict[str, object]) -> list[str]:
    """Возвращает компактный список предупреждений по кандидату импорта."""

    warning_messages: list[str] = []
    if candidate_payload.get("needsManualReview") is True:
        warning_messages.append("Candidate payload still requests manual review.")
    return warning_messages


def _build_review_summary(
    candidate_payload: dict[str, object],
    *,
    source_type: str,
    source_file_name: str,
) -> dict[str, object]:
    """Строит компактный review summary для staged import candidate."""

    warning_messages = _build_warning_messages(candidate_payload)
    replaceable_sections = sorted(
        top_level_key
        for top_level_key in candidate_payload.keys()
        if top_level_key not in {"version", "draft", "needsManualReview"}
    )
    import_metadata = candidate_payload.get("importMetadata")
    detected_layout = import_metadata.get("detectedLayout") if isinstance(import_metadata, dict) else None
    detected_sections = import_metadata.get("detectedSections") if isinstance(import_metadata, dict) else None

    return {
        "replaceableSections": replaceable_sections,
        "warningsCount": len(warning_messages),
        "canReplaceFully": bool(replaceable_sections),
        "sourceType": source_type,
        "sourceFileName": source_file_name,
        "detectedLayout": detected_layout if isinstance(detected_layout, str) else None,
        "detectedSections": _pick_string_list(detected_sections),
    }


def _build_normalized_candidate_file_name(source_file_name: str) -> str:
    """Строит имя нормализованного import candidate JSON с сохранением source stem."""

    source_stem = Path(source_file_name).stem or "import-candidate"
    return f"{source_stem}.portfolio.v1.json"


def _pick_string_list(value: object) -> list[str]:
    """Оставляет только строковые значения из потенциально произвольного списка."""

    if not isinstance(value, list):
        return []

    return [entry for entry in value if isinstance(entry, str)]


def _resolve_applied_sections(
    *,
    replace_mode: str,
    replaceable_sections: list[str],
    requested_sections: list[str],
) -> list[str]:
    """Проверяет допустимость набора разделов для partial/full replace."""

    if replace_mode not in {"full_replace", "partial_replace"}:
        raise ValueError("replaceMode must be either 'full_replace' or 'partial_replace'.")

    if replace_mode == "full_replace":
        if not replaceable_sections:
            raise ValueError("Import candidate does not contain replaceable sections.")
        return replaceable_sections

    normalized_sections = sorted({section_name for section_name in requested_sections if section_name})
    if not normalized_sections:
        raise ValueError("Partial replace requires at least one selected section.")

    unknown_sections = [section_name for section_name in normalized_sections if section_name not in replaceable_sections]
    if unknown_sections:
        raise ValueError(
            f"Partial replace received unknown sections: {', '.join(unknown_sections)}.",
        )

    return normalized_sections


def _build_next_draft_payload(
    *,
    replace_mode: str,
    current_payload: dict[str, object],
    candidate_payload: dict[str, object],
    applied_sections: list[str],
) -> dict[str, object]:
    """Строит следующий draft payload после полной или выборочной замены."""

    if replace_mode == "full_replace":
        next_payload = dict(candidate_payload)
    else:
        next_payload = dict(current_payload)
        for section_name in applied_sections:
            next_payload[section_name] = candidate_payload[section_name]

    next_payload["version"] = _extract_content_schema_version(candidate_payload)
    next_payload["draft"] = True
    next_payload["needsManualReview"] = bool(current_payload.get("needsManualReview")) or bool(
        candidate_payload.get("needsManualReview"),
    )
    return next_payload
