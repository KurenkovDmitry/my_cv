"""SQLAlchemy-репозиторий агрегированной анонимной аналитики."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.analytics_models import (
    SectionClickDaily,
    SectionClickTotal,
    SectionViewDaily,
    SectionViewTotal,
    SessionDaily,
    SessionTotal,
)
from app.modules.analytics.constants import ACTION_LABELS, SECTION_LABELS, TOP_ANALYTICS_LIMIT
from app.modules.analytics.domain.entities import (
    AnalyticsSectionClickEvent,
    AnalyticsSectionViewEvent,
    AnalyticsSessionEvent,
)
from app.modules.analytics.domain.repository import AnalyticsRepository


def _series_label(event_day: date) -> str:
    """Преобразует дату агрегата в подпись оси графика."""

    return event_day.strftime("%m-%d")


def _localized_label_for(key: str, labels: dict[str, dict[str, str]]) -> dict[str, str]:
    """Возвращает заранее известную локализованную подпись или нейтральный fallback."""

    return labels.get(key, {"ru": key, "en": key})


class SqlAlchemyAnalyticsRepository:
    """Читает и пишет только агрегаты аналитики без хранения сырых access-логов."""

    def __init__(
        self,
        read_database_session: AsyncSession | None = None,
        write_database_session: AsyncSession | None = None,
    ) -> None:
        self._read_database_session = read_database_session
        self._write_database_session = write_database_session

    async def get_dashboard_snapshot(self) -> dict[str, object]:
        """Строит dashboard snapshot из daily- и total-агрегатов PostgreSQL."""

        read_database_session = self._require_read_database_session()
        sessions_last_7_days = await self._query_daily_series(
            database_session=read_database_session,
            model=SessionDaily,
            value_column=SessionDaily.session_count,
            blocked_column=SessionDaily.blocked_count,
        )
        views_last_7_days = await self._query_daily_series(
            database_session=read_database_session,
            model=SectionViewDaily,
            value_column=SectionViewDaily.view_count,
            blocked_column=SectionViewDaily.blocked_count,
        )
        clicks_last_7_days = await self._query_daily_series(
            database_session=read_database_session,
            model=SectionClickDaily,
            value_column=SectionClickDaily.click_count,
            blocked_column=SectionClickDaily.blocked_count,
        )
        top_sections = await self._query_top_sections(database_session=read_database_session)
        top_actions = await self._query_top_actions(database_session=read_database_session)
        all_time_totals = await self._query_all_time_totals(database_session=read_database_session)

        return {
            "sourceKind": "postgres",
            "sessionsLast7Days": sessions_last_7_days,
            "viewsLast7Days": views_last_7_days,
            "clicksLast7Days": clicks_last_7_days,
            "topSections": top_sections,
            "topActions": top_actions,
            "allTimeTotals": all_time_totals,
        }

    async def ingest_session_event(
        self,
        event: AnalyticsSessionEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSessionEvent] | None = None,
    ) -> None:
        """Пишет session daily/total-агрегаты и при необходимости откатывает всплеск."""

        write_database_session = self._require_write_database_session()
        session_daily_insert = insert(SessionDaily).values(
            event_day=event.occurred_at.date(),
            entry_route_key=event.entry_route_key,
            locale_code=event.locale_code,
            consent_state=event.consent_state,
            storage_mode=event.storage_mode,
            session_count=0 if blocked else 1,
            blocked_count=1 if blocked else 0,
            rollback_count=0,
        )
        session_daily_upsert = session_daily_insert.on_conflict_do_update(
            constraint="pk_session_daily",
            set_={
                "session_count": SessionDaily.session_count + session_daily_insert.excluded.session_count,
                "blocked_count": SessionDaily.blocked_count + session_daily_insert.excluded.blocked_count,
                "updated_at": func.now(),
            },
        )

        try:
            await write_database_session.execute(session_daily_upsert)

            if not blocked:
                session_total_insert = insert(SessionTotal).values(
                    entry_route_key=event.entry_route_key,
                    locale_code=event.locale_code,
                    consent_state=event.consent_state,
                    storage_mode=event.storage_mode,
                    session_count_total=1,
                )
                session_total_upsert = session_total_insert.on_conflict_do_update(
                    constraint="pk_session_total",
                    set_={
                        "session_count_total": SessionTotal.session_count_total
                        + session_total_insert.excluded.session_count_total,
                        "updated_at": func.now(),
                    },
                )
                await write_database_session.execute(session_total_upsert)

            if rollback_events:
                await self._rollback_session_events(
                    database_session=write_database_session,
                    rollback_events=rollback_events,
                )

            await write_database_session.commit()
        except SQLAlchemyError:
            await write_database_session.rollback()
            raise

    async def ingest_section_view_event(
        self,
        event: AnalyticsSectionViewEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionViewEvent] | None = None,
    ) -> None:
        """Пишет section view daily/total-агрегаты и при необходимости откатывает всплеск."""

        write_database_session = self._require_write_database_session()
        section_view_daily_insert = insert(SectionViewDaily).values(
            event_day=event.occurred_at.date(),
            route_key=event.route_key,
            section_key=event.section_key,
            locale_code=event.locale_code,
            view_source=event.view_source,
            view_count=0 if blocked else 1,
            blocked_count=1 if blocked else 0,
            rollback_count=0,
            last_anomaly_at=event.occurred_at if blocked else None,
        )
        section_view_daily_upsert = section_view_daily_insert.on_conflict_do_update(
            constraint="pk_section_view_daily",
            set_={
                "view_count": SectionViewDaily.view_count + section_view_daily_insert.excluded.view_count,
                "blocked_count": SectionViewDaily.blocked_count + section_view_daily_insert.excluded.blocked_count,
                "last_anomaly_at": section_view_daily_insert.excluded.last_anomaly_at,
                "updated_at": func.now(),
            },
        )

        try:
            await write_database_session.execute(section_view_daily_upsert)

            if not blocked:
                section_view_total_insert = insert(SectionViewTotal).values(
                    route_key=event.route_key,
                    section_key=event.section_key,
                    locale_code=event.locale_code,
                    view_source=event.view_source,
                    view_count_total=1,
                )
                section_view_total_upsert = section_view_total_insert.on_conflict_do_update(
                    constraint="pk_section_view_total",
                    set_={
                        "view_count_total": SectionViewTotal.view_count_total
                        + section_view_total_insert.excluded.view_count_total,
                        "updated_at": func.now(),
                    },
                )
                await write_database_session.execute(section_view_total_upsert)

            if rollback_events:
                await self._rollback_section_view_events(
                    database_session=write_database_session,
                    rollback_events=rollback_events,
                )

            await write_database_session.commit()
        except SQLAlchemyError:
            await write_database_session.rollback()
            raise

    async def ingest_section_click_event(
        self,
        event: AnalyticsSectionClickEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionClickEvent] | None = None,
    ) -> None:
        """Пишет section click daily/total-агрегаты и при необходимости откатывает всплеск."""

        write_database_session = self._require_write_database_session()
        section_click_daily_insert = insert(SectionClickDaily).values(
            event_day=event.occurred_at.date(),
            route_key=event.route_key,
            section_key=event.section_key,
            action_key=event.action_key,
            locale_code=event.locale_code,
            click_count=0 if blocked else 1,
            blocked_count=1 if blocked else 0,
            rollback_count=0,
            last_anomaly_at=event.occurred_at if blocked else None,
        )
        section_click_daily_upsert = section_click_daily_insert.on_conflict_do_update(
            constraint="pk_section_click_daily",
            set_={
                "click_count": SectionClickDaily.click_count + section_click_daily_insert.excluded.click_count,
                "blocked_count": SectionClickDaily.blocked_count + section_click_daily_insert.excluded.blocked_count,
                "last_anomaly_at": section_click_daily_insert.excluded.last_anomaly_at,
                "updated_at": func.now(),
            },
        )

        try:
            await write_database_session.execute(section_click_daily_upsert)

            if not blocked:
                section_click_total_insert = insert(SectionClickTotal).values(
                    route_key=event.route_key,
                    section_key=event.section_key,
                    action_key=event.action_key,
                    locale_code=event.locale_code,
                    click_count_total=1,
                )
                section_click_total_upsert = section_click_total_insert.on_conflict_do_update(
                    constraint="pk_section_click_total",
                    set_={
                        "click_count_total": SectionClickTotal.click_count_total
                        + section_click_total_insert.excluded.click_count_total,
                        "updated_at": func.now(),
                    },
                )
                await write_database_session.execute(section_click_total_upsert)

            if rollback_events:
                await self._rollback_section_click_events(
                    database_session=write_database_session,
                    rollback_events=rollback_events,
                )

            await write_database_session.commit()
        except SQLAlchemyError:
            await write_database_session.rollback()
            raise

    async def _query_daily_series(
        self,
        database_session: AsyncSession,
        model: type[SessionDaily] | type[SectionViewDaily] | type[SectionClickDaily],
        value_column: object,
        blocked_column: object,
    ) -> list[dict[str, int | str]]:
        """Возвращает последние семь дней accepted и blocked значений для нужного daily-агрегата."""

        today = datetime.now(tz=timezone.utc).date()
        start_day = today - timedelta(days=6)
        daily_series_query = (
            select(
                model.event_day.label("event_day"),
                func.coalesce(func.sum(value_column), 0).label("value"),
                func.coalesce(func.sum(blocked_column), 0).label("blocked_value"),
            )
            .where(model.event_day >= start_day, model.event_day <= today)
            .group_by(model.event_day)
            .order_by(model.event_day.asc())
        )
        daily_series_result = await database_session.execute(daily_series_query)
        daily_rows = daily_series_result.all()
        daily_map = {
            daily_row.event_day: {
                "value": int(daily_row.value),
                "blockedValue": int(daily_row.blocked_value),
            }
            for daily_row in daily_rows
        }

        return [
            {
                "label": _series_label(day_value),
                "value": int(daily_map.get(day_value, {}).get("value", 0)),
                "blockedValue": int(daily_map.get(day_value, {}).get("blockedValue", 0)),
            }
            for day_value in (start_day + timedelta(days=delta) for delta in range(7))
        ]

    async def _query_top_sections(self, database_session: AsyncSession) -> list[dict[str, object]]:
        """Возвращает топ секций по all-time просмотрам с локализованными подписями."""

        total_expression = func.coalesce(func.sum(SectionViewTotal.view_count_total), 0)
        top_sections_query = (
            select(
                SectionViewTotal.section_key.label("section_key"),
                total_expression.label("total"),
            )
            .group_by(SectionViewTotal.section_key)
            .order_by(total_expression.desc(), SectionViewTotal.section_key.asc())
            .limit(TOP_ANALYTICS_LIMIT)
        )
        top_sections_result = await database_session.execute(top_sections_query)

        return [
            {
                "key": top_section_row.section_key,
                "label": _localized_label_for(top_section_row.section_key, SECTION_LABELS),
                "total": int(top_section_row.total),
            }
            for top_section_row in top_sections_result.all()
        ]

    async def _query_top_actions(self, database_session: AsyncSession) -> list[dict[str, object]]:
        """Возвращает топ действий по all-time кликам с локализованными подписями."""

        total_expression = func.coalesce(func.sum(SectionClickTotal.click_count_total), 0)
        top_actions_query = (
            select(
                SectionClickTotal.action_key.label("action_key"),
                total_expression.label("total"),
            )
            .group_by(SectionClickTotal.action_key)
            .order_by(total_expression.desc(), SectionClickTotal.action_key.asc())
            .limit(TOP_ANALYTICS_LIMIT)
        )
        top_actions_result = await database_session.execute(top_actions_query)

        return [
            {
                "key": top_action_row.action_key,
                "label": _localized_label_for(top_action_row.action_key, ACTION_LABELS),
                "total": int(top_action_row.total),
            }
            for top_action_row in top_actions_result.all()
        ]

    async def _query_all_time_totals(self, database_session: AsyncSession) -> dict[str, int]:
        """Возвращает компактные all-time total-метрики для главных карточек админки."""

        sessions_total_result = await database_session.execute(
            select(func.coalesce(func.sum(SessionTotal.session_count_total), 0))
        )
        section_views_total_result = await database_session.execute(
            select(func.coalesce(func.sum(SectionViewTotal.view_count_total), 0))
        )
        section_clicks_total_result = await database_session.execute(
            select(func.coalesce(func.sum(SectionClickTotal.click_count_total), 0))
        )

        return {
            "sessions": int(sessions_total_result.scalar_one() or 0),
            "sectionViews": int(section_views_total_result.scalar_one() or 0),
            "sectionClicks": int(section_clicks_total_result.scalar_one() or 0),
        }

    async def _rollback_session_events(
        self,
        database_session: AsyncSession,
        rollback_events: list[AnalyticsSessionEvent],
    ) -> None:
        """Откатывает ранее принятые session-события после выявленного подозрительного всплеска."""

        daily_aggregate_map: dict[tuple[date, str, str, str, str], int] = defaultdict(int)
        total_aggregate_map: dict[tuple[str, str, str, str], int] = defaultdict(int)

        for rollback_event in rollback_events:
            daily_aggregate_map[
                (
                    rollback_event.occurred_at.date(),
                    rollback_event.entry_route_key,
                    rollback_event.locale_code,
                    rollback_event.consent_state,
                    rollback_event.storage_mode,
                )
            ] += 1
            total_aggregate_map[
                (
                    rollback_event.entry_route_key,
                    rollback_event.locale_code,
                    rollback_event.consent_state,
                    rollback_event.storage_mode,
                )
            ] += 1

        for aggregate_key, aggregate_count in daily_aggregate_map.items():
            event_day, entry_route_key, locale_code, consent_state, storage_mode = aggregate_key
            await database_session.execute(
                update(SessionDaily)
                .where(
                    SessionDaily.event_day == event_day,
                    SessionDaily.entry_route_key == entry_route_key,
                    SessionDaily.locale_code == locale_code,
                    SessionDaily.consent_state == consent_state,
                    SessionDaily.storage_mode == storage_mode,
                )
                .values(
                    session_count=func.greatest(SessionDaily.session_count - aggregate_count, 0),
                    rollback_count=SessionDaily.rollback_count + aggregate_count,
                    updated_at=func.now(),
                )
            )

        for aggregate_key, aggregate_count in total_aggregate_map.items():
            entry_route_key, locale_code, consent_state, storage_mode = aggregate_key
            await database_session.execute(
                update(SessionTotal)
                .where(
                    SessionTotal.entry_route_key == entry_route_key,
                    SessionTotal.locale_code == locale_code,
                    SessionTotal.consent_state == consent_state,
                    SessionTotal.storage_mode == storage_mode,
                )
                .values(
                    session_count_total=func.greatest(SessionTotal.session_count_total - aggregate_count, 0),
                    updated_at=func.now(),
                )
            )

    async def _rollback_section_view_events(
        self,
        database_session: AsyncSession,
        rollback_events: list[AnalyticsSectionViewEvent],
    ) -> None:
        """Откатывает ранее принятые просмотры секций после выявленного всплеска."""

        daily_aggregate_map: dict[tuple[date, str, str, str, str], int] = defaultdict(int)
        total_aggregate_map: dict[tuple[str, str, str, str], int] = defaultdict(int)

        for rollback_event in rollback_events:
            daily_aggregate_map[
                (
                    rollback_event.occurred_at.date(),
                    rollback_event.route_key,
                    rollback_event.section_key,
                    rollback_event.locale_code,
                    rollback_event.view_source,
                )
            ] += 1
            total_aggregate_map[
                (
                    rollback_event.route_key,
                    rollback_event.section_key,
                    rollback_event.locale_code,
                    rollback_event.view_source,
                )
            ] += 1

        for aggregate_key, aggregate_count in daily_aggregate_map.items():
            event_day, route_key, section_key, locale_code, view_source = aggregate_key
            await database_session.execute(
                update(SectionViewDaily)
                .where(
                    SectionViewDaily.event_day == event_day,
                    SectionViewDaily.route_key == route_key,
                    SectionViewDaily.section_key == section_key,
                    SectionViewDaily.locale_code == locale_code,
                    SectionViewDaily.view_source == view_source,
                )
                .values(
                    view_count=func.greatest(SectionViewDaily.view_count - aggregate_count, 0),
                    rollback_count=SectionViewDaily.rollback_count + aggregate_count,
                    last_anomaly_at=func.now(),
                    updated_at=func.now(),
                )
            )

        for aggregate_key, aggregate_count in total_aggregate_map.items():
            route_key, section_key, locale_code, view_source = aggregate_key
            await database_session.execute(
                update(SectionViewTotal)
                .where(
                    SectionViewTotal.route_key == route_key,
                    SectionViewTotal.section_key == section_key,
                    SectionViewTotal.locale_code == locale_code,
                    SectionViewTotal.view_source == view_source,
                )
                .values(
                    view_count_total=func.greatest(SectionViewTotal.view_count_total - aggregate_count, 0),
                    updated_at=func.now(),
                )
            )

    async def _rollback_section_click_events(
        self,
        database_session: AsyncSession,
        rollback_events: list[AnalyticsSectionClickEvent],
    ) -> None:
        """Откатывает ранее принятые клики действий после выявленного всплеска."""

        daily_aggregate_map: dict[tuple[date, str, str, str, str], int] = defaultdict(int)
        total_aggregate_map: dict[tuple[str, str, str, str], int] = defaultdict(int)

        for rollback_event in rollback_events:
            daily_aggregate_map[
                (
                    rollback_event.occurred_at.date(),
                    rollback_event.route_key,
                    rollback_event.section_key,
                    rollback_event.action_key,
                    rollback_event.locale_code,
                )
            ] += 1
            total_aggregate_map[
                (
                    rollback_event.route_key,
                    rollback_event.section_key,
                    rollback_event.action_key,
                    rollback_event.locale_code,
                )
            ] += 1

        for aggregate_key, aggregate_count in daily_aggregate_map.items():
            event_day, route_key, section_key, action_key, locale_code = aggregate_key
            await database_session.execute(
                update(SectionClickDaily)
                .where(
                    SectionClickDaily.event_day == event_day,
                    SectionClickDaily.route_key == route_key,
                    SectionClickDaily.section_key == section_key,
                    SectionClickDaily.action_key == action_key,
                    SectionClickDaily.locale_code == locale_code,
                )
                .values(
                    click_count=func.greatest(SectionClickDaily.click_count - aggregate_count, 0),
                    rollback_count=SectionClickDaily.rollback_count + aggregate_count,
                    last_anomaly_at=func.now(),
                    updated_at=func.now(),
                )
            )

        for aggregate_key, aggregate_count in total_aggregate_map.items():
            route_key, section_key, action_key, locale_code = aggregate_key
            await database_session.execute(
                update(SectionClickTotal)
                .where(
                    SectionClickTotal.route_key == route_key,
                    SectionClickTotal.section_key == section_key,
                    SectionClickTotal.action_key == action_key,
                    SectionClickTotal.locale_code == locale_code,
                )
                .values(
                    click_count_total=func.greatest(SectionClickTotal.click_count_total - aggregate_count, 0),
                    updated_at=func.now(),
                )
            )

    def _require_read_database_session(self) -> AsyncSession:
        """Гарантирует, что read-only код не запустится без read-role подключения."""

        if self._read_database_session is None:
            raise RuntimeError("Read database session is required for analytics summary queries.")

        return self._read_database_session

    def _require_write_database_session(self) -> AsyncSession:
        """Гарантирует, что mutation-path аналитики не запустится без write-role подключения."""

        if self._write_database_session is None:
            raise RuntimeError("Write database session is required for analytics ingest queries.")

        return self._write_database_session


class FallbackAnalyticsRepository:
    """Сначала пытается читать и писать PostgreSQL, а при сбое переходит в in-memory fallback."""

    def __init__(
        self,
        primary_repository: AnalyticsRepository,
        fallback_repository: AnalyticsRepository,
    ) -> None:
        self._primary_repository = primary_repository
        self._fallback_repository = fallback_repository

    async def get_dashboard_snapshot(self) -> dict[str, object]:
        """Возвращает snapshot из PostgreSQL или fallback-источника, если БД недоступна."""

        try:
            return await self._primary_repository.get_dashboard_snapshot()
        except (SQLAlchemyError, RuntimeError):
            return await self._fallback_repository.get_dashboard_snapshot()

    async def ingest_session_event(
        self,
        event: AnalyticsSessionEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSessionEvent] | None = None,
    ) -> None:
        """Пишет session-агрегаты в PostgreSQL или fallback-источник."""

        try:
            await self._primary_repository.ingest_session_event(
                event=event,
                blocked=blocked,
                rollback_events=rollback_events,
            )
        except (SQLAlchemyError, RuntimeError):
            await self._fallback_repository.ingest_session_event(
                event=event,
                blocked=blocked,
                rollback_events=rollback_events,
            )

    async def ingest_section_view_event(
        self,
        event: AnalyticsSectionViewEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionViewEvent] | None = None,
    ) -> None:
        """Пишет view-агрегаты в PostgreSQL или fallback-источник."""

        try:
            await self._primary_repository.ingest_section_view_event(
                event=event,
                blocked=blocked,
                rollback_events=rollback_events,
            )
        except (SQLAlchemyError, RuntimeError):
            await self._fallback_repository.ingest_section_view_event(
                event=event,
                blocked=blocked,
                rollback_events=rollback_events,
            )

    async def ingest_section_click_event(
        self,
        event: AnalyticsSectionClickEvent,
        blocked: bool = False,
        rollback_events: list[AnalyticsSectionClickEvent] | None = None,
    ) -> None:
        """Пишет click-агрегаты в PostgreSQL или fallback-источник."""

        try:
            await self._primary_repository.ingest_section_click_event(
                event=event,
                blocked=blocked,
                rollback_events=rollback_events,
            )
        except (SQLAlchemyError, RuntimeError):
            await self._fallback_repository.ingest_section_click_event(
                event=event,
                blocked=blocked,
                rollback_events=rollback_events,
            )
