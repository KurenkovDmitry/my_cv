"""Unit-тесты SQLAlchemy-репозитория контентного snapshot-модуля."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.content.domain.repository import ContentSnapshotNotFoundError
from app.modules.content.infrastructure.preview_repository import InMemoryContentRepository
from app.modules.content.infrastructure.sqlalchemy_repository import (
    FallbackContentRepository,
    SqlAlchemyContentRepository,
)


class FakeScalarResult:
    """Минимальная заглушка результата SQLAlchemy execute для unit-тестов без реальной БД."""

    def __init__(self, model: object | None) -> None:
        self._model = model

    def scalar_one_or_none(self) -> object | None:
        """Возвращает заранее подготовленную ORM-подобную модель."""

        return self._model


class FakeAsyncSession:
    """Подменяет AsyncSession и возвращает детерминированный результат execute."""

    def __init__(self, model: object | None) -> None:
        self._model = model

    async def execute(self, statement: object) -> FakeScalarResult:
        """Игнорирует SQL-выражение и возвращает подготовленную модель."""

        return FakeScalarResult(model=self._model)


class MissingPrimaryRepository:
    """Имитирует пустой основной источник данных до первичного наполнения БД."""

    async def get_snapshot(self, snapshot_kind: str):  # type: ignore[no-untyped-def]
        raise ContentSnapshotNotFoundError(f"Snapshot '{snapshot_kind}' is missing.")


@pytest.mark.asyncio
async def test_sqlalchemy_content_repository_maps_snapshot_model() -> None:
    """Проверяет, что SQLAlchemy-репозиторий нормализует ORM-модель в API-совместимую сущность."""

    fake_snapshot_model = SimpleNamespace(
        snapshot_kind="published",
        content_schema_version="portfolio.v1",
        content_checksum_sha256="checksum-value",
        updated_at=datetime(2026, 8, 3, 16, 5, tzinfo=timezone.utc),
        created_at=datetime(2026, 8, 3, 16, 0, tzinfo=timezone.utc),
        is_active=True,
        content_json={"version": "portfolio.v1", "draft": False},
    )
    repository = SqlAlchemyContentRepository(database_session=FakeAsyncSession(model=fake_snapshot_model))  # type: ignore[arg-type]

    snapshot_record = await repository.get_snapshot(snapshot_kind="published")

    assert snapshot_record.snapshot_kind == "published"
    assert snapshot_record.content_schema_version == "portfolio.v1"
    assert snapshot_record.content_checksum_sha256 == "checksum-value"
    assert snapshot_record.updated_at == "2026-08-03T16:05:00Z"
    assert snapshot_record.payload == {"version": "portfolio.v1", "draft": False}


@pytest.mark.asyncio
async def test_fallback_content_repository_uses_preview_when_primary_is_empty() -> None:
    """Проверяет, что fallback-репозиторий не ломает SSR, если БД еще не наполнена."""

    repository = FallbackContentRepository(
        primary_repository=MissingPrimaryRepository(),  # type: ignore[arg-type]
        fallback_repository=InMemoryContentRepository(),
    )

    snapshot_record = await repository.get_snapshot(snapshot_kind="draft")

    assert snapshot_record.snapshot_kind == "draft"
    assert snapshot_record.content_schema_version == "portfolio.v1"
    assert snapshot_record.payload["draft"] is True
