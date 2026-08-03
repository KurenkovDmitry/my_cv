"""ORM-модели публичного контура контента и медиа."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.database.base import Base


class PortfolioSnapshot(Base):
    """Текущий опубликованный или черновой слепок сайта для SSR и админки."""

    __tablename__ = "portfolio_snapshot"
    __table_args__ = (
        UniqueConstraint("snapshot_kind", name="uq_portfolio_snapshot_snapshot_kind"),
        CheckConstraint(
            "jsonb_typeof(published_locale_codes) = 'array'",
            name="portfolio_snapshot_published_locale_codes_array",
        ),
        Index("ix_portfolio_snapshot_is_active_snapshot_kind", "is_active", "snapshot_kind"),
        {"schema": "public", "comment": "Актуальный слепок публичного контента для SSR, preview и экспорта."},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Технический первичный ключ записи слепка.",
    )
    snapshot_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Тип слепка: published или draft.",
    )
    content_schema_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Версия схемы контента внутри content_json.",
    )
    content_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Полный актуальный контент сайта в jsonb для частого чтения без join.",
    )
    content_checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Контрольная сумма слепка для ETag, целостности и инвалидирования кэша.",
    )
    published_locale_codes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Список реально опубликованных локалей в компактном виде.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Флаг активного слепка для безопасного переключения runtime-состояния.",
    )
    published_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Момент публикации текущего слепка.",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания строки слепка.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего изменения слепка.",
    )


class MediaAsset(Base):
    """Реестр файлов и медиа, которые участвуют в публичной выдаче и импорте."""

    __tablename__ = "media_asset"
    __table_args__ = (
        UniqueConstraint("storage_path", name="uq_media_asset_storage_path"),
        UniqueConstraint("checksum_sha256", name="uq_media_asset_checksum_sha256"),
        Index("ix_media_asset_asset_kind", "asset_kind"),
        {
            "schema": "public",
            "comment": "Единый реестр файлов и медиа с минимальным набором метаданных.",
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Стабильный идентификатор ассета.",
    )
    asset_kind: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Тип ассета: avatar, project_cover, resume_source, open_graph_image и другие.",
    )
    storage_disk: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="local",
        server_default="local",
        comment="Тип хранилища файла, например local или object-storage.",
    )
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Путь к файлу внутри выбранного хранилища.",
    )
    public_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Готовая публичная ссылка, если файл уже доступен напрямую.",
    )
    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="MIME-тип файла для безопасной отдачи и валидации.",
    )
    original_filename: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Исходное имя загруженного файла для админки и диагностики.",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Размер файла в байтах для контроля лимитов сервера.",
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Контрольная сумма файла для дедупликации и целостности.",
    )
    image_metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Необязательные метаданные изображения: размеры, цвета и другие свойства.",
    )
    alt_json: Mapped[dict[str, str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Локализованные alt-тексты без вынесения в отдельные таблицы.",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время регистрации ассета.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего обновления метаданных ассета.",
    )
