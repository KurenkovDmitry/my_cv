"""Router агрегированной обезличенной аналитики."""

from fastapi import APIRouter, Depends, Request

from app.config.settings import Settings, get_settings
from app.modules.analytics.api.dependencies import (
    get_analytics_event_service,
    get_analytics_summary_service,
)
from app.modules.analytics.api.requests import (
    SectionClickEventIngestRequest,
    SectionViewEventIngestRequest,
    SessionEventIngestRequest,
)
from app.modules.analytics.api.responses import (
    AnalyticsEventIngestResponse,
    AnalyticsEventResultResponse,
    AnalyticsSummaryResponse,
)
from app.modules.analytics.api.traffic_filter import resolve_analytics_ignore_reason
from app.modules.analytics.application.service import AnalyticsService
from app.modules.authentication.application.admin_session_service import get_admin_session_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    analytics_service: AnalyticsService = Depends(get_analytics_summary_service),
) -> AnalyticsSummaryResponse:
    """Возвращает admin snapshot обезличенной аналитики и all-time total-метрики."""

    return AnalyticsSummaryResponse(snapshot=await analytics_service.get_dashboard_snapshot())


@router.post("/events/session", response_model=AnalyticsEventIngestResponse)
async def ingest_session_event(
    request_payload: SessionEventIngestRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    analytics_service: AnalyticsService = Depends(get_analytics_event_service),
) -> AnalyticsEventIngestResponse:
    """Принимает старт анонимной сессии после подтвержденного consent."""

    ignored_reason = _resolve_request_ignore_reason(request, settings)
    if ignored_reason:
        return _blocked_event_response(ignored_reason)
    result = await analytics_service.register_session_event(
        entry_route_key=request_payload.event.entry_route_key,
        locale_code=request_payload.event.locale_code,
        consent_state=request_payload.event.consent_state,
        storage_mode=request_payload.event.storage_mode,
        session_nonce=request_payload.event.session_nonce,
    )
    return AnalyticsEventIngestResponse(
        result=AnalyticsEventResultResponse(
            status=result.status,
            blockedReason=result.blocked_reason,
        )
    )


@router.post("/events/section-view", response_model=AnalyticsEventIngestResponse)
async def ingest_section_view_event(
    request_payload: SectionViewEventIngestRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    analytics_service: AnalyticsService = Depends(get_analytics_event_service),
) -> AnalyticsEventIngestResponse:
    """Принимает анонимный просмотр секции и обновляет агрегаты."""

    ignored_reason = _resolve_request_ignore_reason(request, settings)
    if ignored_reason:
        return _blocked_event_response(ignored_reason)
    result = await analytics_service.register_section_view_event(
        route_key=request_payload.event.route_key,
        section_key=request_payload.event.section_key,
        locale_code=request_payload.event.locale_code,
        view_source=request_payload.event.view_source,
        session_nonce=request_payload.event.session_nonce,
    )
    return AnalyticsEventIngestResponse(
        result=AnalyticsEventResultResponse(
            status=result.status,
            blockedReason=result.blocked_reason,
        )
    )


@router.post("/events/section-click", response_model=AnalyticsEventIngestResponse)
async def ingest_section_click_event(
    request_payload: SectionClickEventIngestRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    analytics_service: AnalyticsService = Depends(get_analytics_event_service),
) -> AnalyticsEventIngestResponse:
    """Принимает анонимный клик по CTA и обновляет агрегаты."""

    ignored_reason = _resolve_request_ignore_reason(request, settings)
    if ignored_reason:
        return _blocked_event_response(ignored_reason)
    result = await analytics_service.register_section_click_event(
        route_key=request_payload.event.route_key,
        section_key=request_payload.event.section_key,
        action_key=request_payload.event.action_key,
        locale_code=request_payload.event.locale_code,
        session_nonce=request_payload.event.session_nonce,
    )
    return AnalyticsEventIngestResponse(
        result=AnalyticsEventResultResponse(
            status=result.status,
            blockedReason=result.blocked_reason,
        )
    )


def _resolve_request_ignore_reason(request: Request, settings: Settings) -> str | None:
    """Исключает владельца, тесты и локальную разработку из публичных счётчиков."""

    return resolve_analytics_ignore_reason(
        environment=settings.environment,
        track_non_production=settings.analytics_track_non_production,
        user_agent=request.headers.get("User-Agent", ""),
        marked_as_test=request.headers.get("X-Portfolio-Test-Traffic", "") == "1",
        has_admin_session=get_admin_session_service().read_session_from_request(request) is not None,
    )


def _blocked_event_response(reason: str) -> AnalyticsEventIngestResponse:
    """Возвращает единообразный ответ для служебного события без записи в storage."""

    return AnalyticsEventIngestResponse(
        result=AnalyticsEventResultResponse(status="blocked", blockedReason=reason),
    )
