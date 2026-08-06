"""Admin router snapshot-модуля контента."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from app.config.settings import Settings, get_settings
from app.modules.content.api.dependencies import (
    get_content_admin_service,
    get_content_service,
)
from app.modules.content.api.requests import DraftSnapshotUpsertRequest
from app.modules.content.api.responses import (
    AdminPublishResponse,
    ContentAssetListResponse,
    ContentAssetResponseItem,
    PublicPortfolioResponse,
)
from app.modules.content.application.admin_service import ContentAdminService
from app.modules.content.application.service import ContentService
from app.modules.content.domain.asset_storage import ContentAssetStorage, StoredContentAsset
from app.modules.content.domain.entities import PortfolioSnapshotRecord
from app.modules.content.domain.repository import ContentSnapshotNotFoundError
from app.modules.content.infrastructure.local_asset_storage import ContentAssetNotFoundError
from app.modules.content.infrastructure.dependencies import get_content_asset_storage
from app.modules.system.api.responses import BackupArtifactResponseItem
from app.modules.system.domain.entities import BackupArtifactRecord

router = APIRouter(prefix="/content", tags=["content-admin"])
_PUBLIC_ASSET_PATH_PREFIX = "/api/public/portfolio/assets"


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


def _map_asset_response_item(asset_item: StoredContentAsset) -> ContentAssetResponseItem:
    """Преобразует внутренние metadata файла в безопасный admin API-ответ."""

    return ContentAssetResponseItem(
        assetId=asset_item.asset_id,
        fileName=asset_item.file_name,
        mediaType=asset_item.media_type,
        fileSizeBytes=asset_item.file_size_bytes,
        checksumSha256=asset_item.checksum_sha256,
        publicPath=f"{_PUBLIC_ASSET_PATH_PREFIX}/{asset_item.asset_id}",
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


@router.get("/assets", response_model=ContentAssetListResponse)
async def list_content_assets(
    asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> ContentAssetListResponse:
    """Возвращает реестр загруженных подтверждений и изображений."""

    asset_items = await asset_storage.list_assets()
    return ContentAssetListResponse(
        items=[_map_asset_response_item(asset_item) for asset_item in asset_items],
    )


@router.post(
    "/assets",
    response_model=ContentAssetResponseItem,
    status_code=status.HTTP_201_CREATED,
)
async def upload_content_asset(
    request: Request,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    content_admin_service: ContentAdminService = Depends(get_content_admin_service),
) -> ContentAssetResponseItem:
    """Загружает подтверждение или изображение с лимитом размера и проверкой сигнатуры."""

    document_bytes = await file.read(settings.content_asset_max_bytes + 1)
    await file.close()
    try:
        stored_asset = await content_admin_service.upload_asset(
            file_name=file.filename or "document",
            document_bytes=document_bytes,
            requested_media_type=file.content_type,
            actor_login=_resolve_actor_login(request),
            request_id=getattr(request.state, "request_id", None),
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return _map_asset_response_item(stored_asset)


@router.delete("/assets/{asset_id}", response_model=ContentAssetResponseItem)
async def delete_content_asset(
    asset_id: str,
    request: Request,
    content_admin_service: ContentAdminService = Depends(get_content_admin_service),
) -> ContentAssetResponseItem:
    """Удаляет выбранный файл; UI предварительно должен удалить ссылки на него из draft."""

    try:
        deleted_asset = await content_admin_service.delete_asset(
            asset_id=asset_id,
            actor_login=_resolve_actor_login(request),
            request_id=getattr(request.state, "request_id", None),
        )
    except ContentAssetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _map_asset_response_item(deleted_asset)
