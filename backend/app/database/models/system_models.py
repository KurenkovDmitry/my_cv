"""ORM-модели служебного контура админки."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.database.base import Base


class BackupArtifact(Base):
    """Реестр backup/export-артефактов, которые хранятся как файлы, а не как контент в БД."""

    __tablename__ = "backup_artifact"
    __table_args__ = (
        UniqueConstraint("storage_path", name="uq_backup_artifact_storage_path"),
        UniqueConstraint("checksum_sha256", name="uq_backup_artifact_checksum_sha256"),
        Index("ix_backup_artifact_created_at", "created_at"),
        Index("ix_backup_artifact_snapshot_kind_created_at", "snapshot_kind", "created_at"),
        {
            "schema": "system",
            "comment": "Реестр backup/export-файлов для скачивания, сравнения и обратного импорта.",
        },
    )

    backup_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Первичный ключ backup-артефакта.",
    )
    backup_kind: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="export_bundle",
        server_default="export_bundle",
        comment="Тип backup-файла: export_bundle, pre_replace_backup, manual_backup.",
    )
    storage_disk: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="local",
        server_default="local",
        comment="Тип хранилища backup-файла.",
    )
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Путь к backup-файлу для скачивания, сравнения и импорта.",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Размер backup-артефакта в байтах.",
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Контрольная сумма backup-файла для проверки целостности.",
    )
    content_schema_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Версия формата export/import bundle.",
    )
    snapshot_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Состояние слепка, из которого создан backup: draft, published, before_replace.",
    )
    snapshot_checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Контрольная сумма контентного слепка, попавшего в backup.",
    )
    source_resume_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.media_asset.id", ondelete="SET NULL"),
        nullable=True,
        comment="Ссылка на исходный asset резюме, если backup был построен вокруг него.",
    )
    backup_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Компактная сводка backup-файла без хранения его содержимого в БД.",
    )
    created_by_actor: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Кто создал backup через админку или pipeline.",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Момент создания backup.",
    )


class ImportCandidate(Base):
    """Staged import-кандидат для workflow контроля версий и выборочной замены контента."""

    __tablename__ = "import_candidate"
    __table_args__ = (
        UniqueConstraint("storage_path", name="uq_import_candidate_storage_path"),
        UniqueConstraint("checksum_sha256", name="uq_import_candidate_checksum_sha256"),
        Index("ix_import_candidate_expires_at", "expires_at"),
        {
            "schema": "system",
            "comment": "Metadata staged import-кандидатов, где сами payload лежат в файлах.",
        },
    )

    import_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Идентификатор импорт-кандидата.",
    )
    storage_disk: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="local",
        server_default="local",
        comment="Тип хранилища импортируемого bundle-файла.",
    )
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Путь к импортируемому файлу на диске или в объектном хранилище.",
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Контрольная сумма импортируемого файла.",
    )
    content_schema_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Версия импортируемого контентного формата.",
    )
    parse_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Статус разбора импортируемого файла: parsed, warning, failed.",
    )
    review_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Краткая сводка кандидата для review в админке.",
    )
    created_by_actor: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Кто загрузил файл на review.",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания импорт-кандидата.",
    )
    expires_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Момент, после которого staged import можно автоматически удалить.",
    )


class AdminContentState(Base):
    """Служебный singleton-state админского контура контента и импорта."""

    __tablename__ = "admin_content_state"
    __table_args__ = (
        {
            "schema": "system",
            "comment": "Служебное состояние админки и импорта, не участвующее в SSR как основной источник.",
        },
    )

    state_key: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Ключ singleton-состояния, например content_admin.",
    )
    source_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Вынесенное служебное состояние админки, импорта, warnings и manual overrides.",
    )
    last_import_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Результат последнего импорта в админском контуре.",
    )
    last_imported_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего завершенного импорта.",
    )
    pending_import_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("system.import_candidate.import_candidate_id", ondelete="SET NULL"),
        nullable=True,
        comment="Импорт-кандидат, который еще находится в review.",
    )
    current_backup_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("system.backup_artifact.backup_id", ondelete="SET NULL"),
        nullable=True,
        comment="Последний созданный backup bundle для быстрых сценариев rollback.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего обновления служебного состояния админки.",
    )


class RuntimeHealthSnapshot(Base):
    """Fallback-слепок health-метрик, если Grafana не поднята или сервер маломощный."""

    __tablename__ = "runtime_health_snapshot"
    __table_args__ = (
        {
            "schema": "system",
            "comment": "Компактный fallback-источник health-состояния для админки.",
        },
    )

    snapshot_key: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Ключ singleton-снимка, например current.",
    )
    health_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Короткий актуальный статус сервисов и среды выполнения.",
    )
    source_kind: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Источник health snapshot: internal-probe, prometheus-exporter или manual-check.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего обновления health snapshot.",
    )
