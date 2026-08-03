"""Response-модели агрегированной аналитики."""

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsEventResultResponse(BaseModel):
    """Результат ingest одного анонимного события."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    blocked_reason: str | None = Field(default=None, alias="blockedReason")


class AnalyticsEventIngestResponse(BaseModel):
    """Ответ ingest endpoint-а аналитики."""

    result: AnalyticsEventResultResponse


class AnalyticsSummaryResponse(BaseModel):
    """Снимок агрегированной аналитики для админского dashboard."""

    snapshot: dict[str, object]
