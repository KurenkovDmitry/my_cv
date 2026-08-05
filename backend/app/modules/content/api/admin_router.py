"""Admin router snapshot-модуля контента."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.modules.content.api.dependencies import get_content_admin_service, get_content_service
from app.modules.content.api.requests import DraftSnapshotUpsertRequest
from app.modules.content.api.responses import AdminPublishResponse, PublicPortfolioResponse
from app.modules.content.application.admin_service import ContentAdminService
from app.modules.content.application.service import ContentService
from app.modules.content.domain.entities import PortfolioSnapshotRecord
from app.modules.content.domain.repository import ContentSnapshotNotFoundError
from app.modules.system.api.responses import BackupArtifactResponseItem
from app.modules.system.domain.entities import BackupArtifactRecord

router = APIRouter(prefix="/content", tags=["content-admin"])


def _map_snapshot_response(snapshot: PortfolioSnapshotRecord) -> PublicPortfolioResponse:
    """Преобразует доменный snapshot в стабильный API-ответ."""

    return PublicPortfolioResponse(
        snapshotKind=snapshot.snapshot_kind,
        contentSchemaVersion=snapshot.content_schema_version,
        contentChecksumSha256=snapshot.content_checksum_sha256,
        updatedAt=snapshot.updated_at,
        payload=snapshot.payload,
    )


def _map_backup_response_item(backup_item: BackupArtifactRecord) -> BackupArtifactResponseItem:
    """Преобразует доменную запись backup registry в API-ответ."""

    return BackupArtifactResponseItem(
        backupId=backup_item.backup_id,
        backupKind=backup_item.backup_kind,
        snapshotKind=backup_item.snapshot_kind,
        fileName=backup_item.file_name,
        checksumSha256=backup_item.checksum_sha256,
        contentSchemaVersion=backup_item.content_schema_version,
        fileSizeBytes=backup_item.file_size_bytes,
        createdAt=backup_item.created_at,
        createdByActor=backup_item.created_by_actor,
    )


def _resolve_actor_login(request: Request) -> str:
    """Возвращает человекочитаемый логин актора до подключения полноценной auth-схемы."""

    if hasattr(request.state, "admin_login") and request.state.admin_login:
        return request.state.admin_login

    return request.headers.get("X-Admin-Actor", "admin-ui")


@router.get("/snapshot", response_model=PublicPortfolioResponse)
async def get_admin_snapshot(
    kind: str = Query(default="draft", pattern="^(draft|published)$"),
    content_service: ContentService = Depends(get_content_service),
) -> PublicPortfolioResponse:
    """Возвращает snapshot нужного типа для admin-контура."""

    snapshot = await content_service.get_snapshot(snapshot_kind=kind)
    return _map_snapshot_response(snapshot)


@router.put("/draft", response_model=PublicPortfolioResponse)
async def save_admin_draft_snapshot(
    request_payload: DraftSnapshotUpsertRequest,
    request: Request,
    content_admin_service: ContentAdminService = Depends(get_content_admin_service),
) -> PublicPortfolioResponse:
    """Сохраняет текущий draft snapshot через write-role."""

    saved_snapshot = await content_admin_service.save_draft_snapshot(
        payload=request_payload.payload,
        actor_login=_resolve_actor_login(request),
        request_id=getattr(request.state, "request_id", None),
    )
    return _map_snapshot_response(saved_snapshot)


@router.post("/publish", response_model=AdminPublishResponse, status_code=status.HTTP_200_OK)
async def publish_admin_draft_snapshot(
    request: Request,
    content_admin_service: ContentAdminService = Depends(get_content_admin_service),
) -> AdminPublishResponse:
    """Публикует текущий draft snapshot и создаёт pre-replace backup прошлого published."""

    try:
        published_snapshot, created_backup = await content_admin_service.publish_draft_snapshot(
            actor_login=_resolve_actor_login(request),
            request_id=getattr(request.state, "request_id", None),
        )
    except ContentSnapshotNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return AdminPublishResponse(
        snapshot=_map_snapshot_response(published_snapshot),
        backup=_map_backup_response_item(created_backup) if created_backup else None,
    )
