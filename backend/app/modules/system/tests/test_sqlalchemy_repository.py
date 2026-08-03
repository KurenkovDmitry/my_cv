"""Unit-тесты SQLAlchemy-репозитория служебного admin/system-контура."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.system.domain.repository import SystemStateNotFoundError
from app.modules.system.infrastructure.preview_repository import InMemorySystemRepository
from app.modules.system.infrastructure.sqlalchemy_repository import (
    FallbackSystemRepository,
    SqlAlchemySystemRepository,
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


class MissingSystemStateRepository:
    """Имитирует еще не инициализированный singleton-state в основной БД."""

    async def get_admin_content_state(self):  # type: ignore[no-untyped-def]
        raise SystemStateNotFoundError("Missing content_admin state.")

    async def list_backup_artifacts(self) -> list[dict[str, object]]:
        return []

    async def list_import_candidates(self) -> list[dict[str, object]]:
        return []

    async def get_runtime_health(self) -> dict[str, object]:
        return {}

    async def list_recent_audit_logs(self) -> list[dict[str, object]]:
        return []


@pytest.mark.asyncio
async def test_sqlalchemy_system_repository_merges_runtime_health_columns() -> None:
    """Проверяет, что runtime health дополняется колонками source_kind и updated_at."""

    fake_health_model = SimpleNamespace(
        snapshot_key="current",
        source_kind="internal-probe",
        updated_at=datetime(2026, 8, 3, 15, 40, tzinfo=timezone.utc),
        health_json={
            "services": {"api": "ok", "postgres": "ok", "redis": "ok"},
            "diskFreeMb": 6120,
            "memoryPressure": "low",
            "grafanaEnabled": False,
        },
    )
    repository = SqlAlchemySystemRepository(database_session=FakeAsyncSession(model=fake_health_model))  # type: ignore[arg-type]

    runtime_health_snapshot = await repository.get_runtime_health()

    assert runtime_health_snapshot["sourceKind"] == "internal-probe"
    assert runtime_health_snapshot["updatedAt"] == "2026-08-03T15:40:00Z"
    assert runtime_health_snapshot["diskFreeMb"] == 6120
    assert runtime_health_snapshot["services"] == {"api": "ok", "postgres": "ok", "redis": "ok"}


@pytest.mark.asyncio
async def test_fallback_system_repository_uses_preview_when_state_is_missing() -> None:
    """Проверяет, что админка получает preview-state, если singleton-строка еще не создана."""

    repository = FallbackSystemRepository(
        primary_repository=MissingSystemStateRepository(),  # type: ignore[arg-type]
        fallback_repository=InMemorySystemRepository(),
    )

    admin_content_state = await repository.get_admin_content_state()

    assert admin_content_state.state_key == "content_admin"
    assert admin_content_state.last_import_status == "warning"
    assert admin_content_state.pending_import_candidate_id == "candidate-2026-08-03-resume"
