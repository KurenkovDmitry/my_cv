"""Response-модели snapshot-модуля контента."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.system.api.responses import BackupArtifactResponseItem


class PublicPortfolioResponse(BaseModel):
    """Ответ опубликованного snapshot для SSR и public frontend."""

    model_config = ConfigDict(populate_by_name=True)

    snapshot_kind: str = Field(alias="snapshotKind")
    content_schema_version: str = Field(alias="contentSchemaVersion")
    content_checksum_sha256: str = Field(alias="contentChecksumSha256")
    updated_at: str = Field(alias="updatedAt")
    payload: dict[str, Any]


class AdminPublishResponse(BaseModel):
    """Ответ publish-сценария с опубликованным snapshot и pre-replace backup."""

    snapshot: PublicPortfolioResponse
    backup: BackupArtifactResponseItem | None = None
