"""ORM-модели минимального audit-контура админки."""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class AdminActionLog(Base):
    """Минимальный аудит действий админки без хранения тяжелых runtime-логов."""

    __tablename__ = "admin_action_log"
    __table_args__ = (
        PrimaryKeyConstraint("occurred_at", "log_id", name="pk_admin_action_log"),
        {
            "schema": "audit",
            "comment": "Минимальный журнал действий админки с помесячным партиционированием.",
        },
    )

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        comment="Идентификатор audit-события.",
    )
    occurred_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Время события и ключ партиционирования.",
    )
    actor_subject: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Внешний subject из SSO или JWKS.",
    )
    actor_login: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Читаемый логин или email актера для расследований.",
    )
    action_code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Код операции, например publish_snapshot, delete_backup или apply_import_candidate.",
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Тип сущности, над которой было выполнено действие.",
    )
    entity_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Идентификатор сущности в удобном для UI виде.",
    )
    change_summary_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Краткий diff или summary изменения без хранения полного документа.",
    )
    request_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Связь с API-запросом для поиска в связанных системах наблюдаемости.",
    )
    result_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Итог операции: success, blocked, failed и подобные значения.",
    )
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Редкие служебные детали события без разрастания основной схемы.",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Техническое время записи строки аудита.",
    )
