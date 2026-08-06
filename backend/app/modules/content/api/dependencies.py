"""Dependency-фабрики snapshot-модуля контента."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_read_database_session, get_write_database_session
from app.modules.content.application.admin_service import ContentAdminService
from app.modules.content.application.service import ContentService
from app.modules.content.domain.asset_storage import ContentAssetStorage
from app.modules.content.infrastructure.dependencies import get_content_asset_storage
from app.modules.content.infrastructure.preview_repository import InMemoryContentRepository
from app.modules.content.infrastructure.sqlalchemy_repository import (
    FallbackContentRepository,
    SqlAlchemyContentRepository,
)
from app.modules.system.api.dependencies import get_backup_bundle_storage
from app.modules.system.domain.storage import BackupBundleStorage
from app.modules.system.infrastructure.sqlalchemy_repository import SqlAlchemySystemRepository


def get_content_service(
    database_session: AsyncSession = Depends(get_read_database_session),
) -> ContentService:
    """Собирает content-service с PostgreSQL read-path и безопасным preview-fallback."""

    primary_repository = SqlAlchemyContentRepository(database_session=database_session)
    fallback_repository = InMemoryContentRepository()
    return ContentService(
        content_repository=FallbackContentRepository(
            primary_repository=primary_repository,
            fallback_repository=fallback_repository,
        )
    )


def get_content_admin_service(
    write_database_session: AsyncSession = Depends(get_write_database_session),
    backup_bundle_storage: BackupBundleStorage = Depends(get_backup_bundle_storage),
    content_asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> ContentAdminService:
    """Собирает content-admin service для сохранения draft и publish-сценариев."""

    content_repository = SqlAlchemyContentRepository(database_session=write_database_session)
    system_repository = SqlAlchemySystemRepository(database_session=write_database_session)
    return ContentAdminService(
        database_session=write_database_session,
        content_repository=content_repository,
        system_repository=system_repository,
        backup_storage=backup_bundle_storage,
        asset_storage=content_asset_storage,
    )
