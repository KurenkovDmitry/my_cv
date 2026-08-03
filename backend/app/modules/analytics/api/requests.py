"""Request-модели анонимной аналитики."""

from pydantic import BaseModel, ConfigDict, Field


class SessionEventPayloadRequest(BaseModel):
    """Payload обезличенной сессии."""

    model_config = ConfigDict(populate_by_name=True)

    entry_route_key: str = Field(alias="entryRouteKey")
    locale_code: str = Field(alias="localeCode")
    consent_state: str = Field(alias="consentState")
    storage_mode: str = Field(alias="storageMode")
    session_nonce: str = Field(alias="sessionNonce")
    occurred_at: str = Field(alias="occurredAt")


class SectionViewEventPayloadRequest(BaseModel):
    """Payload обезличенного просмотра секции."""

    model_config = ConfigDict(populate_by_name=True)

    route_key: str = Field(alias="routeKey")
    section_key: str = Field(alias="sectionKey")
    locale_code: str = Field(alias="localeCode")
    view_source: str = Field(alias="viewSource")
    session_nonce: str = Field(alias="sessionNonce")
    occurred_at: str = Field(alias="occurredAt")


class SectionClickEventPayloadRequest(BaseModel):
    """Payload обезличенного клика по действию."""

    model_config = ConfigDict(populate_by_name=True)

    route_key: str = Field(alias="routeKey")
    section_key: str = Field(alias="sectionKey")
    action_key: str = Field(alias="actionKey")
    locale_code: str = Field(alias="localeCode")
    session_nonce: str = Field(alias="sessionNonce")
    occurred_at: str = Field(alias="occurredAt")


class SessionEventIngestRequest(BaseModel):
    """Обёртка ingest-запроса сессии."""

    event: SessionEventPayloadRequest


class SectionViewEventIngestRequest(BaseModel):
    """Обёртка ingest-запроса просмотра секции."""

    event: SectionViewEventPayloadRequest


class SectionClickEventIngestRequest(BaseModel):
    """Обёртка ingest-запроса клика."""

    event: SectionClickEventPayloadRequest
