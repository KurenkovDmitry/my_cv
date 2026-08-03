"""Доменные сущности контентного snapshot-модуля."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class PortfolioSnapshotRecord:
    """Текущий слепок портфолио для SSR и публичного API."""

    snapshot_kind: str
    content_schema_version: str
    content_checksum_sha256: str
    updated_at: str
    payload: dict[str, Any]
