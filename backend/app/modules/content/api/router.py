"""Router snapshot-модуля контента."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.modules.content.api.dependencies import get_content_service
from app.modules.content.api.responses import PublicPortfolioResponse
from app.modules.content.application.service import ContentService
from app.modules.content.domain.asset_storage import ContentAssetStorage
from app.modules.content.infrastructure.local_asset_storage import ContentAssetNotFoundError
from app.modules.content.infrastructure.dependencies import get_content_asset_storage

router = APIRouter(prefix="/portfolio", tags=["content"])


@router.get("", response_model=PublicPortfolioResponse)
async def get_public_portfolio(
    content_service: ContentService = Depends(get_content_service),
) -> PublicPortfolioResponse:
    """Возвращает единый опубликованный snapshot портфолио для SSR и гидратации."""

    snapshot = await content_service.get_public_snapshot()
    return PublicPortfolioResponse(
        snapshotKind=snapshot.snapshot_kind,
        contentSchemaVersion=snapshot.content_schema_version,
        contentChecksumSha256=snapshot.content_checksum_sha256,
        updatedAt=snapshot.updated_at,
        payload=snapshot.payload,
    )


@router.get("/assets/{asset_id}")
async def download_public_content_asset(
    asset_id: str,
    asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> FileResponse:
    """Отдаёт только разрешённые управляемые файлы по непрогнозируемому asset id."""

    try:
        stored_asset = await asset_storage.get_asset(asset_id)
        asset_path = await asset_storage.resolve_asset_path(asset_id)
    except (ContentAssetNotFoundError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return FileResponse(
        path=asset_path,
        filename=stored_asset.file_name,
        media_type=stored_asset.media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
