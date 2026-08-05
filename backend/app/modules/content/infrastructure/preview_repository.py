"""Временный preview-репозиторий контентного snapshot-модуля."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from app.modules.content.domain.entities import PortfolioSnapshotRecord


def _get_preview_json_path() -> Path:
    """Возвращает путь к единому preview JSON, собранному из резюме."""

    return Path(__file__).resolve().parents[5] / "content" / "generated" / "portfolio.preview.json"


@lru_cache(maxsize=1)
def _load_preview_payload() -> dict[str, object]:
    """Читает preview payload с диска и кэширует его между запросами."""

    preview_payload = json.loads(_get_preview_json_path().read_text(encoding="utf-8"))
    if not isinstance(preview_payload, dict):
        raise ValueError("Preview portfolio payload must be a JSON object.")

    return preview_payload


def _build_preview_payload(snapshot_kind: str) -> dict[str, object]:
    """Возвращает копию preview payload с корректным draft-флагом текущего snapshot."""

    preview_payload = deepcopy(_load_preview_payload())
    preview_payload["draft"] = snapshot_kind == "draft"
    return preview_payload


def _build_content_checksum(payload: dict[str, object]) -> str:
    """Строит стабильную контрольную сумму preview payload для fallback-ответа."""

    normalized_payload_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(normalized_payload_bytes).hexdigest()


class InMemoryContentRepository:
    """Возвращает опубликованный или черновой слепок до подключения реальной БД."""

    async def get_snapshot(self, snapshot_kind: str) -> PortfolioSnapshotRecord:
        """Отдаёт fallback snapshot в формате будущего `content_json`-документа."""

        normalized_snapshot_kind = "draft" if snapshot_kind == "draft" else "published"
        payload = _build_preview_payload(normalized_snapshot_kind)

        return PortfolioSnapshotRecord(
            snapshot_kind=normalized_snapshot_kind,
            content_schema_version="portfolio.v1",
            content_checksum_sha256=_build_content_checksum(payload),
            updated_at="2026-08-05T12:00:00Z" if normalized_snapshot_kind == "draft" else "2026-08-05T11:45:00Z",
            payload=payload,
        )
