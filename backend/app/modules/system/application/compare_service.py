"""Application-сервис compare/diff сценариев админки."""

from __future__ import annotations

from app.modules.content.domain.repository import ContentRepository
from app.modules.system.application.bundle_payloads import extract_portfolio_payload
from app.modules.system.domain.diff_engine import ContentDiffEngine, ContentDiffRecord
from app.modules.system.domain.repository import SystemRepository
from app.modules.system.domain.storage import BackupBundleStorage, ImportCandidateStorage


class SystemCompareService:
    """Строит on-demand diff без хранения исторических diff в БД."""

    def __init__(
        self,
        content_repository: ContentRepository,
        system_repository: SystemRepository,
        backup_storage: BackupBundleStorage,
        import_candidate_storage: ImportCandidateStorage,
        content_diff_engine: ContentDiffEngine,
    ) -> None:
        self._content_repository = content_repository
        self._system_repository = system_repository
        self._backup_storage = backup_storage
        self._import_candidate_storage = import_candidate_storage
        self._content_diff_engine = content_diff_engine

    async def compare_backup_to_snapshot(
        self,
        *,
        backup_id: str,
        snapshot_kind: str,
    ) -> ContentDiffRecord:
        """Сравнивает backup bundle и текущий snapshot из БД."""

        backup_record = await self._system_repository.get_backup_artifact(backup_id)
        backup_document = await self._backup_storage.load_bundle_document(backup_record.storage_path)
        backup_payload = extract_portfolio_payload(backup_document)
        snapshot_record = await self._content_repository.get_snapshot(snapshot_kind=snapshot_kind)

        return await self._content_diff_engine.compare(
            left_payload=backup_payload,
            right_payload=snapshot_record.payload,
            left_label=f"backup:{backup_record.file_name}",
            right_label=f"snapshot:{snapshot_kind}",
        )

    async def compare_backup_to_backup(
        self,
        *,
        left_backup_id: str,
        right_backup_id: str,
    ) -> ContentDiffRecord:
        """Сравнивает два backup bundle между собой."""

        left_backup_record = await self._system_repository.get_backup_artifact(left_backup_id)
        right_backup_record = await self._system_repository.get_backup_artifact(right_backup_id)
        left_backup_document = await self._backup_storage.load_bundle_document(left_backup_record.storage_path)
        right_backup_document = await self._backup_storage.load_bundle_document(right_backup_record.storage_path)

        return await self._content_diff_engine.compare(
            left_payload=extract_portfolio_payload(left_backup_document),
            right_payload=extract_portfolio_payload(right_backup_document),
            left_label=f"backup:{left_backup_record.file_name}",
            right_label=f"backup:{right_backup_record.file_name}",
        )

    async def compare_import_candidate_to_snapshot(
        self,
        *,
        import_candidate_id: str,
        snapshot_kind: str,
    ) -> ContentDiffRecord:
        """Сравнивает staged import candidate и текущий snapshot."""

        import_candidate_record = await self._system_repository.get_import_candidate(import_candidate_id)
        import_candidate_document = await self._import_candidate_storage.load_candidate_document(
            import_candidate_record.storage_path,
        )
        import_candidate_payload = extract_portfolio_payload(import_candidate_document)
        snapshot_record = await self._content_repository.get_snapshot(snapshot_kind=snapshot_kind)

        return await self._content_diff_engine.compare(
            left_payload=import_candidate_payload,
            right_payload=snapshot_record.payload,
            left_label=f"candidate:{import_candidate_id}",
            right_label=f"snapshot:{snapshot_kind}",
        )

    async def compare_import_candidate_to_backup(
        self,
        *,
        import_candidate_id: str,
        backup_id: str,
    ) -> ContentDiffRecord:
        """Сравнивает staged import candidate и выбранный backup bundle."""

        import_candidate_record = await self._system_repository.get_import_candidate(import_candidate_id)
        backup_record = await self._system_repository.get_backup_artifact(backup_id)
        import_candidate_document = await self._import_candidate_storage.load_candidate_document(
            import_candidate_record.storage_path,
        )
        backup_document = await self._backup_storage.load_bundle_document(backup_record.storage_path)

        return await self._content_diff_engine.compare(
            left_payload=extract_portfolio_payload(import_candidate_document),
            right_payload=extract_portfolio_payload(backup_document),
            left_label=f"candidate:{import_candidate_id}",
            right_label=f"backup:{backup_record.file_name}",
        )
