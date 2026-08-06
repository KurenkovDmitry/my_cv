"""Application-сервис mutation-path контентной админки."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.application.asset_bundle import (
    build_asset_bundle_entries,
    collect_referenced_asset_ids,
)
from app.modules.content.domain.asset_storage import ContentAssetStorage, StoredContentAsset
from app.modules.content.domain.entities import PortfolioSnapshotRecord
from app.modules.content.domain.repository import (
    ContentAdminRepository,
    ContentSnapshotNotFoundError,
)
from app.modules.system.domain.entities import BackupArtifactRecord
from app.modules.system.domain.repository import SystemAdminRepository
from app.modules.system.domain.storage import BackupBundleStorage


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


class ContentAdminService:
    """Оркестрирует сохранение draft и публикацию published snapshot."""

    def __init__(
        self,
        database_session: AsyncSession,
        content_repository: ContentAdminRepository,
        system_repository: SystemAdminRepository,
        backup_storage: BackupBundleStorage,
        asset_storage: ContentAssetStorage,
    ) -> None:
        self._database_session = database_session
        self._content_repository = content_repository
        self._system_repository = system_repository
        self._backup_storage = backup_storage
        self._asset_storage = asset_storage

    async def upload_asset(
        self,
        *,
        file_name: str,
        document_bytes: bytes,
        requested_media_type: str | None,
        actor_login: str,
        request_id: str | None,
    ) -> StoredContentAsset:
        """Сохраняет проверенный файл и фиксирует административное действие в audit log."""

        occurred_at = datetime.now(timezone.utc)
        stored_asset = await self._asset_storage.write_asset(
            file_name=file_name,
            document_bytes=document_bytes,
            requested_media_type=requested_media_type,
        )
        try:
            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="upload_content_asset",
                entity_type="content_asset",
                entity_key=stored_asset.asset_id,
                result_code="success",
                request_id=request_id,
                change_summary={
                    "fileName": stored_asset.file_name,
                    "mediaType": stored_asset.media_type,
                    "fileSizeBytes": stored_asset.file_size_bytes,
                },
                metadata={"checksumSha256": stored_asset.checksum_sha256},
            )
            await self._database_session.commit()
            return stored_asset
        except Exception:
            await self._database_session.rollback()
            await self._asset_storage.delete_asset(stored_asset.asset_id)
            raise

    async def delete_asset(
        self,
        *,
        asset_id: str,
        actor_login: str,
        request_id: str | None,
    ) -> StoredContentAsset:
        """Удаляет один asset и записывает необратимую операцию в audit log."""

        occurred_at = datetime.now(timezone.utc)
        for snapshot_kind in ("draft", "published"):
            try:
                snapshot_record = await self._content_repository.get_snapshot(
                    snapshot_kind=snapshot_kind,
                )
            except ContentSnapshotNotFoundError:
                continue
            if asset_id in collect_referenced_asset_ids(snapshot_record.payload):
                raise ValueError(
                    f"Content asset '{asset_id}' is still referenced by {snapshot_kind} snapshot.",
                )
        deleted_asset = await self._asset_storage.delete_asset(asset_id)
        try:
            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="delete_content_asset",
                entity_type="content_asset",
                entity_key=asset_id,
                result_code="success",
                request_id=request_id,
                change_summary={"fileName": deleted_asset.file_name},
                metadata={"checksumSha256": deleted_asset.checksum_sha256},
            )
            await self._database_session.commit()
            return deleted_asset
        except Exception:
            await self._database_session.rollback()
            raise

    async def save_draft_snapshot(
        self,
        *,
        payload: dict[str, object],
        actor_login: str,
        request_id: str | None,
    ) -> PortfolioSnapshotRecord:
        """Сохраняет текущий draft snapshot и пишет audit-запись."""

        occurred_at = datetime.now(timezone.utc)

        try:
            saved_snapshot = await self._content_repository.save_snapshot(
                snapshot_kind="draft",
                payload=payload,
                content_schema_version=_extract_content_schema_version(payload),
                content_checksum_sha256=_build_content_checksum(payload),
                published_locale_codes=_extract_published_locale_codes(payload),
                is_active=True,
                published_at=None,
            )
            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="save_draft_snapshot",
                entity_type="portfolio_snapshot",
                entity_key="draft",
                result_code="success",
                request_id=request_id,
                change_summary={
                    "contentChecksumSha256": saved_snapshot.content_checksum_sha256,
                    "contentSchemaVersion": saved_snapshot.content_schema_version,
                },
                metadata=None,
            )
            await self._database_session.commit()
            return saved_snapshot
        except Exception:
            await self._database_session.rollback()
            raise

    async def publish_draft_snapshot(
        self,
        *,
        actor_login: str,
        request_id: str | None,
    ) -> tuple[PortfolioSnapshotRecord, BackupArtifactRecord | None]:
        """Публикует текущий draft и перед заменой создаёт file-backed backup предыдущего published."""

        occurred_at = datetime.now(timezone.utc)
        created_backup: BackupArtifactRecord | None = None

        try:
            draft_snapshot = await self._content_repository.get_snapshot(snapshot_kind="draft")

            try:
                current_published_snapshot = await self._content_repository.get_snapshot(snapshot_kind="published")
            except ContentSnapshotNotFoundError:
                current_published_snapshot = None

            if current_published_snapshot is not None:
                created_backup = await self._create_backup_from_snapshot(
                    snapshot_record=current_published_snapshot,
                    backup_kind="pre_replace_backup",
                    registry_snapshot_kind="before_replace",
                    actor_login=actor_login,
                )

            published_snapshot = await self._content_repository.save_snapshot(
                snapshot_kind="published",
                payload=draft_snapshot.payload,
                content_schema_version=draft_snapshot.content_schema_version,
                content_checksum_sha256=draft_snapshot.content_checksum_sha256,
                published_locale_codes=_extract_published_locale_codes(draft_snapshot.payload),
                is_active=True,
                published_at=occurred_at,
            )
            await self._system_repository.append_audit_log(
                occurred_at=occurred_at,
                actor_login=actor_login,
                action_code="publish_snapshot",
                entity_type="portfolio_snapshot",
                entity_key="published",
                result_code="success",
                request_id=request_id,
                change_summary={
                    "draftChecksumSha256": draft_snapshot.content_checksum_sha256,
                    "publishedChecksumSha256": published_snapshot.content_checksum_sha256,
                    "backupArtifactId": created_backup.backup_id if created_backup else None,
                },
                metadata={
                    "publishedLocaleCodes": _extract_published_locale_codes(draft_snapshot.payload),
                },
            )
            await self._database_session.commit()
            return published_snapshot, created_backup
        except Exception:
            await self._database_session.rollback()
            if created_backup is not None:
                await self._backup_storage.delete_bundle(created_backup.storage_path)
            raise

    async def _create_backup_from_snapshot(
        self,
        *,
        snapshot_record: PortfolioSnapshotRecord,
        backup_kind: str,
        registry_snapshot_kind: str,
        actor_login: str,
    ) -> BackupArtifactRecord:
        """Создаёт file-backed backup по текущему snapshot без сохранения полного payload в БД."""

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
