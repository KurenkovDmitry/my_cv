"""ORM-модели агрегированной обезличенной аналитики."""

from __future__ import annotations

from sqlalchemy import BigInteger, Date, DateTime, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class SessionDaily(Base):
    """Дневной агрегат анонимных валидных сессий."""

    __tablename__ = "session_daily"
    __table_args__ = (
        PrimaryKeyConstraint(
            "event_day",
            "entry_route_key",
            "locale_code",
            "consent_state",
            "storage_mode",
            name="pk_session_daily",
        ),
        {
            "schema": "analytics",
            "comment": "Агрегированное число валидных обезличенных сессий за день.",
        },
    )

    event_day: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
        comment="День, к которому относится агрегат.",
    )
    entry_route_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Маршрут первого входа в сессию.",
    )
    locale_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Локаль, по которой учитывается сессия.",
    )
    consent_state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="accepted",
        server_default="accepted",
        comment="Состояние согласия. В текущем контуре фактически хранится только accepted.",
    )
    storage_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Где клиент сохранил анонимный технический маркер согласия или сессии.",
    )
    session_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Число валидных засчитанных сессий.",
    )
    blocked_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Количество сессий, отброшенных антинакруточной логикой.",
    )
    rollback_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Количество ранее учтенных сессий, откатанных после выявления аномалии.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего обновления агрегата.",
    )


class SessionTotal(Base):
    """All-time total по анонимным сессиям после очистки старых daily-partitions."""

    __tablename__ = "session_total"
    __table_args__ = (
        PrimaryKeyConstraint(
            "entry_route_key",
            "locale_code",
            "consent_state",
            "storage_mode",
            name="pk_session_total",
        ),
        {
            "schema": "analytics",
            "comment": "Накопительная all-time статистика по сессиям для админских графиков.",
        },
    )

    entry_route_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Маршрут первого входа в сессию.",
    )
    locale_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Локаль сессии.",
    )
    consent_state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="accepted",
        server_default="accepted",
        comment="Состояние согласия. В текущей модели предполагается accepted.",
    )
    storage_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Способ сохранения анонимного технического маркера.",
    )
    session_count_total: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="All-time total по сессиям для админского dashboard.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего обновления накопительного агрегата.",
    )


class SectionViewDaily(Base):
    """Дневной агрегат просмотров разделов сайта."""

    __tablename__ = "section_view_daily"
    __table_args__ = (
        PrimaryKeyConstraint(
            "event_day",
            "route_key",
            "section_key",
            "locale_code",
            "view_source",
            name="pk_section_view_daily",
        ),
        {
            "schema": "analytics",
            "comment": "Агрегированные просмотры разделов сайта по дням.",
        },
    )

    event_day: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
        comment="День агрегирования просмотров.",
    )
    route_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Маршрут страницы, на которой показан раздел.",
    )
    section_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Ключ секции внутри страницы, например hero или projects_grid.",
    )
    locale_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Локаль, в которой был просмотрен раздел.",
    )
    view_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Способ засчета просмотра: ssr_render, viewport_visible или rehydrated_visible.",
    )
    view_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Число валидных просмотров секции.",
    )
    blocked_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Подозрительные просмотры, не попавшие в итоговый счетчик.",
    )
    rollback_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Просмотры, откатанные после аномального всплеска.",
    )
    last_anomaly_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Последний момент срабатывания антинакруточной защиты.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время обновления агрегата просмотров.",
    )


class SectionViewTotal(Base):
    """All-time total по просмотрам секций после очистки старых daily-partitions."""

    __tablename__ = "section_view_total"
    __table_args__ = (
        PrimaryKeyConstraint(
            "route_key",
            "section_key",
            "locale_code",
            "view_source",
            name="pk_section_view_total",
        ),
        {
            "schema": "analytics",
            "comment": "Накопительные all-time просмотры секций для admin dashboard.",
        },
    )

    route_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Маршрут страницы.",
    )
    section_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Ключ секции внутри страницы.",
    )
    locale_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Локаль просмотра.",
    )
    view_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Сценарий засчета просмотра.",
    )
    view_count_total: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Общий накопительный счетчик просмотров секции.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего обновления all-time агрегата просмотров.",
    )


class SectionClickDaily(Base):
    """Дневной агрегат кликов по интерактивным действиям."""

    __tablename__ = "section_click_daily"
    __table_args__ = (
        PrimaryKeyConstraint(
            "event_day",
            "route_key",
            "section_key",
            "action_key",
            "locale_code",
            name="pk_section_click_daily",
        ),
        {
            "schema": "analytics",
            "comment": "Агрегированные клики по действиям на сайте по дням.",
        },
    )

    event_day: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
        comment="День агрегирования кликов.",
    )
    route_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Маршрут страницы, на которой произошел клик.",
    )
    section_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Ключ секции, внутри которой произошел клик.",
    )
    action_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Ключ действия, например open_project, download_cv или switch_locale.",
    )
    locale_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Локаль клика.",
    )
    click_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Число валидных кликов.",
    )
    blocked_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Подозрительные клики, отброшенные антинакруточной логикой.",
    )
    rollback_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Клики, откатанные после аномального всплеска.",
    )
    last_anomaly_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Последний момент срабатывания антиспам-защиты по кликам.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время обновления агрегата кликов.",
    )


class SectionClickTotal(Base):
    """All-time total по кликам после очистки старых daily-partitions."""

    __tablename__ = "section_click_total"
    __table_args__ = (
        PrimaryKeyConstraint(
            "route_key",
            "section_key",
            "action_key",
            "locale_code",
            name="pk_section_click_total",
        ),
        {
            "schema": "analytics",
            "comment": "Накопительные all-time клики по действиям для админских графиков.",
        },
    )

    route_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Маршрут страницы.",
    )
    section_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Ключ секции внутри страницы.",
    )
    action_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Ключ пользовательского действия внутри секции.",
    )
    locale_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Локаль, в которой произошел клик.",
    )
    click_count_total: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Общий накопительный счетчик кликов.",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время последнего обновления all-time агрегата кликов.",
    )
