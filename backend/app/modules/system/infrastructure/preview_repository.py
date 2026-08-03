"""Preview-репозиторий служебных данных админки."""

from app.modules.system.domain.entities import (
    AdminContentStateRecord,
    BackupArtifactRecord,
    ImportCandidateRecord,
)
from app.modules.system.domain.repository import BackupArtifactNotFoundError, ImportCandidateNotFoundError


class InMemorySystemRepository:
    """Возвращает preview-данные для admin dashboard до подключения реальной БД."""

    async def get_admin_content_state(self) -> AdminContentStateRecord:
        """Служебное состояние контентного контура."""

        return AdminContentStateRecord(
            state_key="content_admin",
            source_metadata={
                "lastSourceType": "resume_pdf",
                "lastSourceFilename": "resume-2026-07-22.pdf",
                "warnings": [
                    "Не удалось однозначно определить даты по одному месту работы.",
                ],
                "manualOverrides": [
                    "profile.summary.ru",
                    "projects[0].summary.en",
                ],
            },
            last_import_status="warning",
            last_imported_at="2026-08-03T15:00:00Z",
            pending_import_candidate_id="candidate-2026-08-03-resume",
            current_backup_artifact_id="backup-2026-08-03-published",
            updated_at="2026-08-03T15:05:00Z",
        )

    async def list_backup_artifacts(self) -> list[BackupArtifactRecord]:
        """Список importable/exportable backup bundle-артефактов."""

        return [
            BackupArtifactRecord(
                backup_id="backup-2026-08-03-published",
                backup_kind="export_bundle",
                snapshot_kind="published",
                file_name="portfolio-published-2026-08-03.bundle.json",
                storage_path="published/2026/08/portfolio-published-2026-08-03.bundle.json",
                checksum_sha256="9cbf9d5d0c5f7f3566d69d6f4bc1acfe8f2ef8c710d10e6380ad8f14b9d94f0f",
                content_schema_version="portfolio.v1",
                file_size_bytes=82432,
                created_at="2026-08-03T14:15:00Z",
                created_by_actor="admin@example.com",
            ),
            BackupArtifactRecord(
                backup_id="backup-2026-08-02-before-replace",
                backup_kind="pre_replace_backup",
                snapshot_kind="before_replace",
                file_name="portfolio-before-replace-2026-08-02.bundle.json",
                storage_path="before_replace/2026/08/portfolio-before-replace-2026-08-02.bundle.json",
                checksum_sha256="a4f5c8d6b6b19f66795f6ecae8cf80d6264ed7df51ea0bcd4787fa3f04ea2088",
                content_schema_version="portfolio.v1",
                file_size_bytes=80111,
                created_at="2026-08-02T09:40:00Z",
                created_by_actor="admin@example.com",
            ),
        ]

    async def get_backup_artifact(self, backup_id: str) -> BackupArtifactRecord:
        """Возвращает один preview backup-артефакт или сигнализирует о его отсутствии."""

        for backup_item in await self.list_backup_artifacts():
            if backup_item.backup_id == backup_id:
                return backup_item

        raise BackupArtifactNotFoundError(f"Backup artifact '{backup_id}' is not available.")

    async def list_import_candidates(self) -> list[ImportCandidateRecord]:
        """Список staged import-кандидатов для control version workflow."""

        return [
            ImportCandidateRecord(
                import_candidate_id="candidate-2026-08-03-resume",
                parse_status="warning",
                content_schema_version="portfolio.v1",
                storage_path="preview/candidate-2026-08-03-resume.json",
                checksum_sha256="1d3f0f3f2d2e4f77a46d6a1b9d4a79b3a3428a43ff5f112084d9c8ad1f52e841",
                created_at="2026-08-03T15:00:00Z",
                created_by_actor="admin@example.com",
                review_summary={
                    "replaceableSections": ["profile", "projects", "experience"],
                    "warningsCount": 1,
                    "canReplaceFully": True,
                },
            )
        ]

    async def get_import_candidate(self, import_candidate_id: str) -> ImportCandidateRecord:
        """Возвращает один preview import-кандидат или сигнализирует о его отсутствии."""

        for import_candidate in await self.list_import_candidates():
            if import_candidate.import_candidate_id == import_candidate_id:
                return import_candidate

        raise ImportCandidateNotFoundError(f"Import candidate '{import_candidate_id}' is not available.")

    async def get_runtime_health(self) -> dict[str, object]:
        """Компактный health snapshot, если отдельная Grafana не поднята."""

        return {
            "sourceKind": "internal-probe",
            "updatedAt": "2026-08-03T15:40:00Z",
            "services": {
                "api": "ok",
                "postgres": "ok",
                "redis": "ok",
            },
            "diskFreeMb": 6120,
            "memoryPressure": "low",
            "grafanaEnabled": False,
        }

    async def list_recent_audit_logs(self) -> list[dict[str, object]]:
        """Недавние действия админки для preview-таблицы логов."""

        return [
            {
                "logId": "log-2026-08-03-publish",
                "occurredAt": "2026-08-03T15:12:00Z",
                "actorLogin": "admin@example.com",
                "actionCode": "publish_snapshot",
                "entityType": "portfolio_snapshot",
                "entityKey": "published",
                "resultCode": "success",
            },
            {
                "logId": "log-2026-08-03-import-review",
                "occurredAt": "2026-08-03T15:02:00Z",
                "actorLogin": "admin@example.com",
                "actionCode": "create_import_candidate",
                "entityType": "import_candidate",
                "entityKey": "candidate-2026-08-03-resume",
                "resultCode": "warning",
            },
        ]
