"""Router snapshot-модуля контента."""

from fastapi import APIRouter, Depends

from app.modules.content.api.dependencies import get_content_service
from app.modules.content.api.responses import PublicPortfolioResponse
from app.modules.content.application.service import ContentService

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
