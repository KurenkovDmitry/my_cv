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


class ContentAssetResponseItem(BaseModel):
    """Метаданные управляемого подтверждения или изображения без внутреннего пути."""

    model_config = ConfigDict(populate_by_name=True)

    asset_id: str = Field(alias="assetId")
    file_name: str = Field(alias="fileName")
    media_type: str = Field(alias="mediaType")
    file_size_bytes: int = Field(alias="fileSizeBytes")
    checksum_sha256: str = Field(alias="checksumSha256")
    public_path: str = Field(alias="publicPath")


class ContentAssetListResponse(BaseModel):
    """Список файлов, которыми управляет администратор портфолио."""

    items: list[ContentAssetResponseItem]
