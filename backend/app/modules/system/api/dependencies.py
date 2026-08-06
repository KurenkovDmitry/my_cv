"""Dependency-фабрики служебного admin/system-контура."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.session import get_read_database_session, get_write_database_session
from app.modules.content.domain.asset_storage import ContentAssetStorage
from app.modules.content.infrastructure.dependencies import get_content_asset_storage
from app.modules.content.infrastructure.sqlalchemy_repository import SqlAlchemyContentRepository
from app.modules.system.application.admin_service import SystemAdminService
from app.modules.system.application.compare_service import SystemCompareService
from app.modules.system.application.resume_import_converter import ResumeImportConverter
from app.modules.system.application.service import SystemService
from app.modules.system.domain.diff_engine import ContentDiffEngine
from app.modules.system.domain.storage import BackupBundleStorage, ImportCandidateStorage
from app.modules.system.infrastructure.content_diff_engine import NativeContentDiffEngine
from app.modules.system.infrastructure.local_backup_storage import LocalBackupBundleStorage
from app.modules.system.infrastructure.local_import_candidate_storage import LocalImportCandidateStorage
from app.modules.system.infrastructure.preview_repository import InMemorySystemRepository
from app.modules.system.infrastructure.sqlalchemy_repository import (
    FallbackSystemRepository,
    SqlAlchemySystemRepository,
)


@lru_cache(maxsize=1)
def get_backup_bundle_storage() -> BackupBundleStorage:
    """Возвращает singleton фасада локального backup-storage."""

    return LocalBackupBundleStorage(settings=get_settings())


@lru_cache(maxsize=1)
def get_import_candidate_storage() -> ImportCandidateStorage:
    """Возвращает singleton фасада локального import candidate storage."""

    return LocalImportCandidateStorage(settings=get_settings())


@lru_cache(maxsize=1)
def get_content_diff_engine() -> ContentDiffEngine:
    """Возвращает singleton фасада native/Python compare engine."""

    return NativeContentDiffEngine()


@lru_cache(maxsize=1)
def get_resume_import_converter() -> ResumeImportConverter:
    """Возвращает singleton-адаптер конвертации resume-like документов в `portfolio.v1`."""

    return ResumeImportConverter(settings=get_settings())


def get_system_service(
    database_session: AsyncSession = Depends(get_read_database_session),
) -> SystemService:
    """Собирает system-service с чтением из PostgreSQL и мягким preview-fallback."""

    primary_repository = SqlAlchemySystemRepository(database_session=database_session)
    fallback_repository = InMemorySystemRepository()
    return SystemService(
        system_repository=FallbackSystemRepository(
            primary_repository=primary_repository,
            fallback_repository=fallback_repository,
        )
    )


def get_system_compare_service(
    read_database_session: AsyncSession = Depends(get_read_database_session),
    backup_bundle_storage: BackupBundleStorage = Depends(get_backup_bundle_storage),
    import_candidate_storage: ImportCandidateStorage = Depends(get_import_candidate_storage),
    content_diff_engine: ContentDiffEngine = Depends(get_content_diff_engine),
) -> SystemCompareService:
    """Собирает compare-service на read-role для on-demand diff сценариев."""

    return SystemCompareService(
        content_repository=SqlAlchemyContentRepository(database_session=read_database_session),
        system_repository=FallbackSystemRepository(
            primary_repository=SqlAlchemySystemRepository(database_session=read_database_session),
            fallback_repository=InMemorySystemRepository(),
        ),
        backup_storage=backup_bundle_storage,
        import_candidate_storage=import_candidate_storage,
        content_diff_engine=content_diff_engine,
    )


def get_system_admin_service(
    write_database_session: AsyncSession = Depends(get_write_database_session),
    backup_bundle_storage: BackupBundleStorage = Depends(get_backup_bundle_storage),
    import_candidate_storage: ImportCandidateStorage = Depends(get_import_candidate_storage),
    resume_import_converter: ResumeImportConverter = Depends(get_resume_import_converter),
    content_asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> SystemAdminService:
    """Собирает system-admin service для backup/download/delete и import upload сценариев."""

    return SystemAdminService(
        database_session=write_database_session,
        content_repository=SqlAlchemyContentRepository(database_session=write_database_session),
        system_repository=SqlAlchemySystemRepository(database_session=write_database_session),
        backup_storage=backup_bundle_storage,
        import_candidate_storage=import_candidate_storage,
        resume_import_converter=resume_import_converter,
        asset_storage=content_asset_storage,
    )
