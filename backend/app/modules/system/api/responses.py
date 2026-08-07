"""Response-модели служебного admin/system-контура."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminContentStateSnapshotResponse(BaseModel):
    """Снимок служебного состояния контентной админки."""

    model_config = ConfigDict(populate_by_name=True)

    state_key: str = Field(alias="stateKey")
    source_metadata: dict[str, object] = Field(alias="sourceMetadata")
    last_import_status: str = Field(alias="lastImportStatus")
    last_imported_at: str | None = Field(alias="lastImportedAt")
    pending_import_candidate_id: str | None = Field(alias="pendingImportCandidateId")
    current_backup_artifact_id: str | None = Field(alias="currentBackupArtifactId")
    updated_at: str = Field(alias="updatedAt")


class AdminContentStateResponse(BaseModel):
    """Ответ service-state админки."""

    snapshot: AdminContentStateSnapshotResponse


class BackupArtifactResponseItem(BaseModel):
    """Элемент backup registry или результата mutation-path операции."""

    model_config = ConfigDict(populate_by_name=True)

    backup_id: str = Field(alias="backupId")
    backup_kind: str = Field(alias="backupKind")
    snapshot_kind: str = Field(alias="snapshotKind")
    file_name: str = Field(alias="fileName")
    checksum_sha256: str = Field(alias="checksumSha256")
    content_schema_version: str = Field(alias="contentSchemaVersion")
    file_size_bytes: int = Field(alias="fileSizeBytes")
    created_at: str = Field(alias="createdAt")
    created_by_actor: str = Field(alias="createdByActor")


class BackupArtifactListResponse(BaseModel):
    """Ответ списка backup-артефактов."""

    items: list[BackupArtifactResponseItem]


class BackupArtifactMutationResponse(BaseModel):
    """Ответ create/delete операций по backup registry."""

    item: BackupArtifactResponseItem


class ImportCandidateResponseItem(BaseModel):
    """Элемент staged import candidate registry."""

    model_config = ConfigDict(populate_by_name=True)

    import_candidate_id: str = Field(alias="importCandidateId")
    parse_status: str = Field(alias="parseStatus")
    content_schema_version: str = Field(alias="contentSchemaVersion")
    created_at: str = Field(alias="createdAt")
    created_by_actor: str = Field(alias="createdByActor")
    review_summary: dict[str, object] = Field(alias="reviewSummary")


class ImportCandidateListResponse(BaseModel):
    """Ответ списка staged import-кандидатов."""

    items: list[ImportCandidateResponseItem]


class ImportCandidateMutationResponse(BaseModel):
    """Ответ create/import mutation-path операций staged import candidate."""

    item: ImportCandidateResponseItem


class ImportCandidateFieldReviewItem(BaseModel):
    """Одно изменение поля между текущим draft и import candidate."""

    model_config = ConfigDict(populate_by_name=True)

    path: str
    section: str
    label: str
    operation: str
    change_kind: str = Field(alias="changeKind")
    has_current_value: bool = Field(alias="hasCurrentValue")
    has_candidate_value: bool = Field(alias="hasCandidateValue")
    current_value: Any = Field(alias="currentValue")
    candidate_value: Any = Field(alias="candidateValue")


class ImportCandidateFieldReviewResponse(BaseModel):
    """Git-подобное полевое сравнение candidate с актуальным draft."""

    item: ImportCandidateResponseItem
    fields: list[ImportCandidateFieldReviewItem]


class PortfolioSnapshotResponseItem(BaseModel):
    """Упрощённое snapshot-представление для import replace workflow."""

    model_config = ConfigDict(populate_by_name=True)

    snapshot_kind: str = Field(alias="snapshotKind")
    content_schema_version: str = Field(alias="contentSchemaVersion")
    content_checksum_sha256: str = Field(alias="contentChecksumSha256")
    updated_at: str = Field(alias="updatedAt")
    payload: dict[str, object]


class ContentDiffSummaryResponse(BaseModel):
    """Числовая сводка diff-результата."""

    model_config = ConfigDict(populate_by_name=True)

    changed_paths_count: int = Field(alias="changedPathsCount")
    sections_changed_count: int = Field(alias="sectionsChangedCount")


class ContentDiffSnapshotResponse(BaseModel):
    """Summary diff между двумя документами без хранения diff в БД."""

    model_config = ConfigDict(populate_by_name=True)

    left_label: str = Field(alias="leftLabel")
    right_label: str = Field(alias="rightLabel")
    changed_paths: list[str] = Field(alias="changedPaths")
    sections: list[str]
    summary: ContentDiffSummaryResponse


class ImportCandidateApplyResponse(BaseModel):
    """Ответ применения staged import candidate в текущий draft snapshot."""

    model_config = ConfigDict(populate_by_name=True)

    snapshot: PortfolioSnapshotResponseItem
    backup: BackupArtifactResponseItem | None = None
    item: ImportCandidateResponseItem
    replace_mode: str = Field(alias="replaceMode")
    applied_sections: list[str] = Field(alias="appliedSections")
    applied_fields: list[str] = Field(alias="appliedFields")


class ContentDiffResponse(BaseModel):
    """Ответ compare endpoint'ов админки."""

    diff: ContentDiffSnapshotResponse


class RuntimeHealthResponse(BaseModel):
    """Ответ runtime health snapshot."""

    snapshot: dict[str, object]


class AuditLogListResponse(BaseModel):
    """Ответ последних audit-записей админки."""

    items: list[dict[str, object]]
