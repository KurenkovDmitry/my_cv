"""Request-модели служебного admin/system-контура."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateBackupArtifactRequest(BaseModel):
    """Тело запроса на создание нового backup/export bundle."""

    model_config = ConfigDict(populate_by_name=True)

    snapshot_kind: str = Field(alias="snapshotKind", pattern="^(draft|published)$")
    backup_kind: str = Field(alias="backupKind", pattern="^(export_bundle|manual_backup)$")


class ImportFieldPatchRequest(BaseModel):
    """Одно подтверждённое или вручную исправленное изменение поля."""

    path: str = Field(min_length=1, max_length=512)
    operation: str = Field(pattern="^(set|remove)$")
    value: Any = None


class ApplyImportCandidateRequest(BaseModel):
    """Тело запроса на применение staged import candidate в draft."""

    model_config = ConfigDict(populate_by_name=True)

    replace_mode: str = Field(alias="replaceMode", pattern="^(full_replace|partial_replace|field_replace)$")
    sections: list[str] = Field(default_factory=list)
    fields: list[ImportFieldPatchRequest] = Field(default_factory=list, max_length=2000)
