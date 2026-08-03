"""SQLAlchemy-репозитории snapshot-модуля контента."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.public_models import PortfolioSnapshot
from app.modules.content.domain.entities import PortfolioSnapshotRecord
from app.modules.content.domain.repository import ContentRepository, ContentSnapshotNotFoundError


def _serialize_datetime(value: datetime) -> str:
    """Нормализует datetime в UTC ISO-формат, который стабильно понимают frontend и API-контракты."""

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class SqlAlchemyContentRepository:
    """Читает и изменяет published/draft snapshot через SQLAlchemy."""

    def __init__(self, database_session: AsyncSession) -> None:
        self._database_session = database_session

    async def get_snapshot(self, snapshot_kind: str) -> PortfolioSnapshotRecord:
        """Возвращает последний snapshot нужного типа из таблицы public.portfolio_snapshot."""

        normalized_snapshot_kind = "draft" if snapshot_kind == "draft" else "published"
        snapshot_select = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_kind == normalized_snapshot_kind)
            .order_by(
                PortfolioSnapshot.is_active.desc(),
                PortfolioSnapshot.updated_at.desc(),
                PortfolioSnapshot.created_at.desc(),
            )
            .limit(1)
        )
        snapshot_result = await self._database_session.execute(snapshot_select)
        snapshot_model = snapshot_result.scalar_one_or_none()

        if snapshot_model is None:
            raise ContentSnapshotNotFoundError(
                f"Snapshot with kind '{normalized_snapshot_kind}' is not available in PostgreSQL.",
            )

        return self._map_snapshot_model(snapshot_model=snapshot_model)

    async def save_snapshot(
        self,
        snapshot_kind: str,
        payload: dict[str, object],
        content_schema_version: str,
        content_checksum_sha256: str,
        published_locale_codes: list[str],
        *,
        is_active: bool,
        published_at: datetime | None,
    ) -> PortfolioSnapshotRecord:
        """Создаёт или обновляет единый snapshot указанного типа без немедленного commit."""

        normalized_snapshot_kind = "draft" if snapshot_kind == "draft" else "published"
        existing_snapshot_select = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_kind == normalized_snapshot_kind)
            .limit(1)
        )
        existing_snapshot_result = await self._database_session.execute(existing_snapshot_select)
        snapshot_model = existing_snapshot_result.scalar_one_or_none()

        if snapshot_model is None:
            snapshot_model = PortfolioSnapshot(
                snapshot_kind=normalized_snapshot_kind,
                content_schema_version=content_schema_version,
                content_json=payload,
                content_checksum_sha256=content_checksum_sha256,
                published_locale_codes=published_locale_codes,
                is_active=is_active,
                published_at=published_at,
            )
            self._database_session.add(snapshot_model)
        else:
            snapshot_model.content_schema_version = content_schema_version
            snapshot_model.content_json = payload
            snapshot_model.content_checksum_sha256 = content_checksum_sha256
            snapshot_model.published_locale_codes = published_locale_codes
            snapshot_model.is_active = is_active
            snapshot_model.published_at = published_at
            snapshot_model.updated_at = func.now()

        await self._database_session.flush()
        await self._database_session.refresh(snapshot_model)
        return self._map_snapshot_model(snapshot_model=snapshot_model)

    def _map_snapshot_model(self, snapshot_model: PortfolioSnapshot) -> PortfolioSnapshotRecord:
        """Преобразует ORM-модель в стабильную доменную сущность snapshot-модуля."""

        return PortfolioSnapshotRecord(
            snapshot_kind=snapshot_model.snapshot_kind,
            content_schema_version=snapshot_model.content_schema_version,
            content_checksum_sha256=snapshot_model.content_checksum_sha256,
            updated_at=_serialize_datetime(snapshot_model.updated_at),
            payload=dict(snapshot_model.content_json),
        )


class FallbackContentRepository:
    """Сначала читает PostgreSQL, а при пустой или недоступной БД аккуратно падает в preview-источник."""

    def __init__(
        self,
        primary_repository: ContentRepository,
        fallback_repository: ContentRepository,
    ) -> None:
        self._primary_repository = primary_repository
        self._fallback_repository = fallback_repository

    async def get_snapshot(self, snapshot_kind: str) -> PortfolioSnapshotRecord:
        """Пытается читать production-источник, но не ломает локальную разработку без поднятой БД."""

        try:
            return await self._primary_repository.get_snapshot(snapshot_kind=snapshot_kind)
        except (ContentSnapshotNotFoundError, SQLAlchemyError):
            return await self._fallback_repository.get_snapshot(snapshot_kind=snapshot_kind)
