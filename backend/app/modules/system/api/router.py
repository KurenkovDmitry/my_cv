"""Router служебного admin/system-контура."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.config.settings import Settings, get_settings
from app.modules.content.domain.entities import PortfolioSnapshotRecord
from app.modules.content.domain.repository import ContentSnapshotNotFoundError
from app.modules.system.api.dependencies import (
    get_system_admin_service,
    get_system_compare_service,
    get_system_service,
)
from app.modules.system.api.requests import ApplyImportCandidateRequest, CreateBackupArtifactRequest
from app.modules.system.api.responses import (
    AdminContentStateResponse,
    AdminContentStateSnapshotResponse,
    AuditLogListResponse,
    BackupArtifactListResponse,
    BackupArtifactMutationResponse,
    BackupArtifactResponseItem,
    ContentDiffResponse,
    ContentDiffSnapshotResponse,
    ContentDiffSummaryResponse,
    ImportCandidateApplyResponse,
    ImportCandidateFieldReviewItem,
    ImportCandidateFieldReviewResponse,
    ImportCandidateListResponse,
    ImportCandidateMutationResponse,
    ImportCandidateResponseItem,
    PortfolioSnapshotResponseItem,
    RuntimeHealthResponse,
)
from app.modules.system.application.admin_service import SystemAdminService
from app.modules.system.application.compare_service import SystemCompareService
from app.modules.system.application.service import SystemService
from app.modules.system.domain.diff_engine import ContentDiffRecord
from app.modules.system.domain.entities import BackupArtifactRecord, ImportCandidateRecord
from app.modules.system.domain.repository import (
    BackupArtifactNotFoundError,
    ImportCandidateNotFoundError,
)

router = APIRouter(prefix="/system", tags=["system"])


def _map_snapshot_response(snapshot: PortfolioSnapshotRecord) -> PortfolioSnapshotResponseItem:
    """Преобразует доменный snapshot в API-ответ import workflow."""

    return PortfolioSnapshotResponseItem(
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


def _map_import_candidate_response_item(
    import_candidate_item: ImportCandidateRecord,
) -> ImportCandidateResponseItem:
    """Преобразует staged import candidate в стабильный API-ответ."""

    return ImportCandidateResponseItem(
        importCandidateId=import_candidate_item.import_candidate_id,
        parseStatus=import_candidate_item.parse_status,
        contentSchemaVersion=import_candidate_item.content_schema_version,
        createdAt=import_candidate_item.created_at,
        createdByActor=import_candidate_item.created_by_actor,
        reviewSummary=import_candidate_item.review_summary,
    )


def _map_diff_response(diff_record: ContentDiffRecord) -> ContentDiffResponse:
    """Преобразует результат native/Python compare engine в API-ответ."""

    return ContentDiffResponse(
        diff=ContentDiffSnapshotResponse(
            leftLabel=diff_record.left_label,
            rightLabel=diff_record.right_label,
            changedPaths=diff_record.changed_paths,
            sections=diff_record.sections,
            summary=ContentDiffSummaryResponse(
                changedPathsCount=diff_record.changed_paths_count,
                sectionsChangedCount=diff_record.sections_changed_count,
            ),
        )
    )


def _resolve_actor_login(request: Request) -> str:
    """Возвращает логин актёра до подключения полноценной auth-схемы."""

    if hasattr(request.state, "admin_login") and request.state.admin_login:
        return request.state.admin_login

    return request.headers.get("X-Admin-Actor", "admin-ui")


@router.get("/content-state", response_model=AdminContentStateResponse)
async def get_admin_content_state(
    system_service: SystemService = Depends(get_system_service),
) -> AdminContentStateResponse:
    """Возвращает служебное состояние контентной админки и импорта."""

    state = await system_service.get_admin_content_state()
    return AdminContentStateResponse(
        snapshot=AdminContentStateSnapshotResponse(
            stateKey=state.state_key,
            sourceMetadata=state.source_metadata,
            lastImportStatus=state.last_import_status,
            lastImportedAt=state.last_imported_at,
            pendingImportCandidateId=state.pending_import_candidate_id,
            currentBackupArtifactId=state.current_backup_artifact_id,
            updatedAt=state.updated_at,
        )
    )


@router.get("/backups", response_model=BackupArtifactListResponse)
async def list_backup_artifacts(
    system_service: SystemService = Depends(get_system_service),
) -> BackupArtifactListResponse:
    """Возвращает backup/export registry для скачивания, удаления и diff-сравнения."""

    backup_items = await system_service.list_backup_artifacts()
    return BackupArtifactListResponse(items=[_map_backup_response_item(backup_item) for backup_item in backup_items])


@router.post("/backups", response_model=BackupArtifactMutationResponse, status_code=status.HTTP_201_CREATED)
async def create_backup_artifact(
    request_payload: CreateBackupArtifactRequest,
    request: Request,
    system_admin_service: SystemAdminService = Depends(get_system_admin_service),
) -> BackupArtifactMutationResponse:
    """Создаёт новый file-backed backup/export bundle."""

    backup_item = await system_admin_service.create_backup_artifact(
        snapshot_kind=request_payload.snapshot_kind,
        backup_kind=request_payload.backup_kind,
        actor_login=_resolve_actor_login(request),
        request_id=getattr(request.state, "request_id", None),
    )
    return BackupArtifactMutationResponse(item=_map_backup_response_item(backup_item))


@router.delete("/backups/{backup_id}", response_model=BackupArtifactMutationResponse)
async def delete_backup_artifact(
    backup_id: str,
    request: Request,
    system_admin_service: SystemAdminService = Depends(get_system_admin_service),
) -> BackupArtifactMutationResponse:
    """Удаляет backup из registry и физически удаляет bundle-файл."""

    try:
        deleted_backup = await system_admin_service.delete_backup_artifact(
            backup_id=backup_id,
            actor_login=_resolve_actor_login(request),
            request_id=getattr(request.state, "request_id", None),
        )
    except BackupArtifactNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return BackupArtifactMutationResponse(item=_map_backup_response_item(deleted_backup))


@router.get("/backups/{backup_id}/download")
async def download_backup_artifact(
    backup_id: str,
    system_admin_service: SystemAdminService = Depends(get_system_admin_service),
) -> FileResponse:
    """Отдаёт backup/export bundle для скачивания из локального storage."""

    try:
        download_path = await system_admin_service.resolve_backup_download_path(backup_id=backup_id)
    except BackupArtifactNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return FileResponse(
        path=download_path,
        filename=download_path.name,
        media_type="application/json",
    )


@router.get("/backups/{backup_id}/compare/snapshot", response_model=ContentDiffResponse)
async def compare_backup_to_snapshot(
    backup_id: str,
    snapshot_kind: str = Query(default="draft", pattern="^(draft|published)$"),
    system_compare_service: SystemCompareService = Depends(get_system_compare_service),
) -> ContentDiffResponse:
    """Сравнивает backup bundle и выбранный snapshot из БД."""

    try:
        diff_record = await system_compare_service.compare_backup_to_snapshot(
            backup_id=backup_id,
            snapshot_kind=snapshot_kind,
        )
    except (BackupArtifactNotFoundError, ContentSnapshotNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _map_diff_response(diff_record)


@router.get("/backups/{left_backup_id}/compare/backup/{right_backup_id}", response_model=ContentDiffResponse)
async def compare_backup_to_backup(
    left_backup_id: str,
    right_backup_id: str,
    system_compare_service: SystemCompareService = Depends(get_system_compare_service),
) -> ContentDiffResponse:
    """Сравнивает два backup bundle между собой без сохранения diff в БД."""

    try:
        diff_record = await system_compare_service.compare_backup_to_backup(
            left_backup_id=left_backup_id,
            right_backup_id=right_backup_id,
        )
    except BackupArtifactNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _map_diff_response(diff_record)


@router.get("/import-candidates", response_model=ImportCandidateListResponse)
async def list_import_candidates(
    system_service: SystemService = Depends(get_system_service),
) -> ImportCandidateListResponse:
    """Возвращает staged import-кандидаты для control version workflow."""

    import_candidate_items = await system_service.list_import_candidates()
    return ImportCandidateListResponse(
        items=[_map_import_candidate_response_item(import_candidate_item) for import_candidate_item in import_candidate_items]
    )


@router.post(
    "/import-candidates",
    response_model=ImportCandidateMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_import_candidate(
    request: Request,
    file: UploadFile = File(...),
    system_admin_service: SystemAdminService = Depends(get_system_admin_service),
) -> ImportCandidateMutationResponse:
    """Создаёт staged import candidate из загруженного export/import bundle."""

    document_bytes = await file.read()
    await file.close()

    if not document_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import candidate file is empty.",
        )

    try:
        import_candidate_item = await system_admin_service.create_import_candidate(
            source_file_name=file.filename or "import-candidate.json",
            document_bytes=document_bytes,
            actor_login=_resolve_actor_login(request),
            request_id=getattr(request.state, "request_id", None),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return ImportCandidateMutationResponse(item=_map_import_candidate_response_item(import_candidate_item))


@router.get("/import-candidates/{import_candidate_id}/compare/snapshot", response_model=ContentDiffResponse)
async def compare_import_candidate_to_snapshot(
    import_candidate_id: str,
    snapshot_kind: str = Query(default="draft", pattern="^(draft|published)$"),
    system_compare_service: SystemCompareService = Depends(get_system_compare_service),
) -> ContentDiffResponse:
    """Сравнивает staged import candidate и текущий snapshot."""

    try:
        diff_record = await system_compare_service.compare_import_candidate_to_snapshot(
            import_candidate_id=import_candidate_id,
            snapshot_kind=snapshot_kind,
        )
    except (ImportCandidateNotFoundError, ContentSnapshotNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _map_diff_response(diff_record)


@router.get(
    "/import-candidates/{import_candidate_id}/field-review",
    response_model=ImportCandidateFieldReviewResponse,
)
async def get_import_candidate_field_review(
    import_candidate_id: str,
    system_admin_service: SystemAdminService = Depends(get_system_admin_service),
) -> ImportCandidateFieldReviewResponse:
    """Возвращает редактируемые различия по каждому полю candidate."""

    try:
        import_candidate_item, review_fields = await system_admin_service.get_import_candidate_field_review(
            import_candidate_id=import_candidate_id,
        )
    except (ImportCandidateNotFoundError, ContentSnapshotNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return ImportCandidateFieldReviewResponse(
        item=_map_import_candidate_response_item(import_candidate_item),
        fields=[ImportCandidateFieldReviewItem.model_validate(review_field) for review_field in review_fields],
    )


@router.get(
    "/import-candidates/{import_candidate_id}/compare/backup/{backup_id}",
    response_model=ContentDiffResponse,
)
async def compare_import_candidate_to_backup(
    import_candidate_id: str,
    backup_id: str,
    system_compare_service: SystemCompareService = Depends(get_system_compare_service),
) -> ContentDiffResponse:
    """Сравнивает staged import candidate и выбранный backup bundle."""

    try:
        diff_record = await system_compare_service.compare_import_candidate_to_backup(
            import_candidate_id=import_candidate_id,
            backup_id=backup_id,
        )
    except (ImportCandidateNotFoundError, BackupArtifactNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _map_diff_response(diff_record)


@router.post(
    "/import-candidates/{import_candidate_id}/apply-to-draft",
    response_model=ImportCandidateApplyResponse,
)
async def apply_import_candidate_to_draft(
    import_candidate_id: str,
    request_payload: ApplyImportCandidateRequest,
    request: Request,
    system_admin_service: SystemAdminService = Depends(get_system_admin_service),
) -> ImportCandidateApplyResponse:
    """Применяет staged import candidate к draft полностью или выборочно по разделам."""

    try:
        saved_snapshot, created_backup, import_candidate_item, applied_sections, applied_fields, replace_mode = (
            await system_admin_service.apply_import_candidate_to_draft(
                import_candidate_id=import_candidate_id,
                replace_mode=request_payload.replace_mode,
                sections=request_payload.sections,
                fields=[field.model_dump() for field in request_payload.fields],
                actor_login=_resolve_actor_login(request),
                request_id=getattr(request.state, "request_id", None),
            )
        )
    except (ImportCandidateNotFoundError, ContentSnapshotNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return ImportCandidateApplyResponse(
        snapshot=_map_snapshot_response(saved_snapshot),
        backup=_map_backup_response_item(created_backup) if created_backup else None,
        item=_map_import_candidate_response_item(import_candidate_item),
        replaceMode=replace_mode,
        appliedSections=applied_sections,
        appliedFields=applied_fields,
    )


@router.get("/runtime-health", response_model=RuntimeHealthResponse)
async def get_runtime_health(
    settings: Settings = Depends(get_settings),
    system_service: SystemService = Depends(get_system_service),
) -> RuntimeHealthResponse:
    """Возвращает runtime health snapshot или fallback без тяжёлой Grafana."""

    runtime_health_snapshot = await system_service.get_runtime_health()
    runtime_health_snapshot["grafanaEnabled"] = settings.enable_grafana_integration
    return RuntimeHealthResponse(snapshot=runtime_health_snapshot)


@router.get("/audit-log", response_model=AuditLogListResponse)
async def list_recent_audit_logs(
    system_service: SystemService = Depends(get_system_service),
) -> AuditLogListResponse:
    """Возвращает недавние audit-записи для admin logs."""

    return AuditLogListResponse(items=await system_service.list_recent_audit_logs())
