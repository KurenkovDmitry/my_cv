"""Сериализация управляемых файлов внутрь переносимого backup bundle."""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from app.modules.content.domain.asset_storage import ContentAssetStorage

_ASSET_ID_FIELD_SUFFIX = "assetid"


def collect_referenced_asset_ids(payload: object) -> list[str]:
    """Рекурсивно собирает уникальные asset id из всей расширяемой модели портфолио."""

    collected_asset_ids: set[str] = set()

    def visit(current_value: object) -> None:
        if isinstance(current_value, dict):
            for field_name, field_value in current_value.items():
                if (
                    isinstance(field_name, str)
                    and field_name.lower().endswith(_ASSET_ID_FIELD_SUFFIX)
                    and isinstance(field_value, str)
                    and field_value
                ):
                    collected_asset_ids.add(field_value)
                visit(field_value)
        elif isinstance(current_value, list):
            for nested_value in current_value:
                visit(nested_value)

    visit(payload)
    return sorted(collected_asset_ids)


async def build_asset_bundle_entries(
    payload: dict[str, object],
    asset_storage: ContentAssetStorage,
) -> list[dict[str, object]]:
    """Встраивает все файлы snapshot в JSON backup как base64 с контрольной суммой."""

    bundle_entries: list[dict[str, object]] = []
    for asset_id in collect_referenced_asset_ids(payload):
        stored_asset = await asset_storage.get_asset(asset_id)
        document_bytes = await asset_storage.read_asset_bytes(asset_id)
        bundle_entries.append(
            {
                "assetId": stored_asset.asset_id,
                "fileName": stored_asset.file_name,
                "mediaType": stored_asset.media_type,
                "fileSizeBytes": stored_asset.file_size_bytes,
                "checksumSha256": stored_asset.checksum_sha256,
                "sourceKind": stored_asset.source_kind,
                "contentBase64": base64.b64encode(document_bytes).decode("ascii"),
            }
        )
    return bundle_entries


def extract_bundled_assets(document_payload: dict[str, Any]) -> list[dict[str, object]]:
    """Извлекает валидные объектные записи assets из bundle, сохраняя совместимость с v1."""

    raw_assets = document_payload.get("assets")
    if not isinstance(raw_assets, list):
        return []
    return [dict(asset_entry) for asset_entry in raw_assets if isinstance(asset_entry, dict)]


async def restore_bundled_assets(
    asset_entries: list[dict[str, object]],
    asset_storage: ContentAssetStorage,
) -> list[str]:
    """Восстанавливает файлы backup под прежними id и возвращает id новых объектов."""

    restored_asset_ids: list[str] = []
    for asset_entry in asset_entries:
        asset_id = _require_string(asset_entry, "assetId")
        file_name = _require_string(asset_entry, "fileName")
        media_type = _require_string(asset_entry, "mediaType")
        content_base64 = _require_string(asset_entry, "contentBase64")
        expected_checksum = _require_string(asset_entry, "checksumSha256")
        try:
            existing_asset = await asset_storage.get_asset(asset_id)
        except FileNotFoundError:
            existing_asset = None

        document_bytes = base64.b64decode(content_base64, validate=True)
        actual_checksum = hashlib.sha256(document_bytes).hexdigest()
        if actual_checksum != expected_checksum:
            raise ValueError(f"Bundled asset '{asset_id}' checksum is invalid.")

        stored_asset = await asset_storage.write_asset(
            file_name=file_name,
            document_bytes=document_bytes,
            requested_media_type=media_type,
            preferred_asset_id=asset_id,
            source_kind=str(asset_entry.get("sourceKind", "backup_restore")),
        )
        if existing_asset is None:
            restored_asset_ids.append(stored_asset.asset_id)
    return restored_asset_ids


def _require_string(asset_entry: dict[str, object], field_name: str) -> str:
    """Читает обязательное строковое поле asset bundle с понятной ошибкой."""

    field_value = asset_entry.get(field_name)
    if not isinstance(field_value, str) or not field_value:
        raise ValueError(f"Bundled asset field '{field_name}' must be a non-empty string.")
    return field_value
