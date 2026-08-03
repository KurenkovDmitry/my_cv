"""Application-сервис служебного контура админки."""

from app.modules.system.domain.entities import (
    AdminContentStateRecord,
    BackupArtifactRecord,
    ImportCandidateRecord,
)
from app.modules.system.domain.repository import SystemRepository


class SystemService:
    """Отдаёт служебные admin-сущности без знания транспортного слоя и конкретной БД."""

    def __init__(self, system_repository: SystemRepository) -> None:
        self._system_repository = system_repository

    async def get_admin_content_state(self) -> AdminContentStateRecord:
        """Возвращает singleton-state контентного контура админки."""

        return await self._system_repository.get_admin_content_state()

    async def list_backup_artifacts(self) -> list[BackupArtifactRecord]:
        """Возвращает backup/export registry."""

        return await self._system_repository.list_backup_artifacts()

    async def list_import_candidates(self) -> list[ImportCandidateRecord]:
        """Возвращает staged import-кандидаты."""

        return await self._system_repository.list_import_candidates()

    async def get_runtime_health(self) -> dict[str, object]:
        """Возвращает runtime health snapshot для admin dashboard."""

        return await self._system_repository.get_runtime_health()

    async def list_recent_audit_logs(self) -> list[dict[str, object]]:
        """Возвращает недавние audit-логи админки."""

        return await self._system_repository.list_recent_audit_logs()
