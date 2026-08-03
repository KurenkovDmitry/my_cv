"""Router агрегированной обезличенной аналитики."""

from fastapi import APIRouter, Depends

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
from app.modules.analytics.application.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    analytics_service: AnalyticsService = Depends(get_analytics_summary_service),
) -> AnalyticsSummaryResponse:
    """Возвращает admin snapshot обезличенной аналитики и all-time total-метрики."""

    return AnalyticsSummaryResponse(snapshot=await analytics_service.get_dashboard_snapshot())


@router.post("/events/session", response_model=AnalyticsEventIngestResponse)
async def ingest_session_event(
    request: SessionEventIngestRequest,
    analytics_service: AnalyticsService = Depends(get_analytics_event_service),
) -> AnalyticsEventIngestResponse:
    """Принимает старт анонимной сессии после подтвержденного consent."""

    result = await analytics_service.register_session_event(
        entry_route_key=request.event.entry_route_key,
        locale_code=request.event.locale_code,
        consent_state=request.event.consent_state,
        storage_mode=request.event.storage_mode,
        session_nonce=request.event.session_nonce,
    )
    return AnalyticsEventIngestResponse(
        result=AnalyticsEventResultResponse(
            status=result.status,
            blockedReason=result.blocked_reason,
        )
    )


@router.post("/events/section-view", response_model=AnalyticsEventIngestResponse)
async def ingest_section_view_event(
    request: SectionViewEventIngestRequest,
    analytics_service: AnalyticsService = Depends(get_analytics_event_service),
) -> AnalyticsEventIngestResponse:
    """Принимает анонимный просмотр секции и обновляет агрегаты."""

    result = await analytics_service.register_section_view_event(
        route_key=request.event.route_key,
        section_key=request.event.section_key,
        locale_code=request.event.locale_code,
        view_source=request.event.view_source,
        session_nonce=request.event.session_nonce,
    )
    return AnalyticsEventIngestResponse(
        result=AnalyticsEventResultResponse(
            status=result.status,
            blockedReason=result.blocked_reason,
        )
    )


@router.post("/events/section-click", response_model=AnalyticsEventIngestResponse)
async def ingest_section_click_event(
    request: SectionClickEventIngestRequest,
    analytics_service: AnalyticsService = Depends(get_analytics_event_service),
) -> AnalyticsEventIngestResponse:
    """Принимает анонимный клик по CTA и обновляет агрегаты."""

    result = await analytics_service.register_section_click_event(
        route_key=request.event.route_key,
        section_key=request.event.section_key,
        action_key=request.event.action_key,
        locale_code=request.event.locale_code,
        session_nonce=request.event.session_nonce,
    )
    return AnalyticsEventIngestResponse(
        result=AnalyticsEventResultResponse(
            status=result.status,
            blockedReason=result.blocked_reason,
        )
    )
