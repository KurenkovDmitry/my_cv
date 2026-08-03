"""Request-модели служебного admin/system-контура."""

from pydantic import BaseModel, ConfigDict, Field


class CreateBackupArtifactRequest(BaseModel):
    """Тело запроса на создание нового backup/export bundle."""

    model_config = ConfigDict(populate_by_name=True)

    snapshot_kind: str = Field(alias="snapshotKind", pattern="^(draft|published)$")
    backup_kind: str = Field(alias="backupKind", pattern="^(export_bundle|manual_backup)$")


class ApplyImportCandidateRequest(BaseModel):
    """Тело запроса на применение staged import candidate в draft."""

    model_config = ConfigDict(populate_by_name=True)

    replace_mode: str = Field(alias="replaceMode", pattern="^(full_replace|partial_replace)$")
    sections: list[str] = Field(default_factory=list)
