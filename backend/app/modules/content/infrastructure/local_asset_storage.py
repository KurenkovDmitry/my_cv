"""Локальная реализация управляемого хранилища файлов контента."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from uuid import uuid4

from app.config.settings import Settings
from app.modules.content.domain.asset_storage import ContentAssetStorage, StoredContentAsset

_ASSET_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
_METADATA_FILE_NAME = "metadata.json"
_PAYLOAD_FILE_NAME = "payload.bin"
_SUPPORTED_MEDIA_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
}
_ALLOWED_SOURCE_KINDS = {"upload", "seed", "custom_avatar", "backup_restore"}
_FORBIDDEN_SVG_ELEMENTS = {"script", "foreignobject", "iframe", "object", "embed"}


class ContentAssetNotFoundError(FileNotFoundError):
    """Сообщает, что управляемый файл с указанным id отсутствует."""


class LocalContentAssetStorage(ContentAssetStorage):
    """Хранит документы и изображения вне frontend-сборки с проверкой сигнатуры файла."""

    def __init__(self, settings: Settings) -> None:
        configured_root = Path(settings.content_asset_storage_path)
        self._root_directory = (
            configured_root if configured_root.is_absolute() else Path.cwd() / configured_root
        )
        self._max_file_size_bytes = settings.content_asset_max_bytes

    async def write_asset(
        self,
        *,
        file_name: str,
        document_bytes: bytes,
        requested_media_type: str | None,
        preferred_asset_id: str | None = None,
        source_kind: str = "upload",
    ) -> StoredContentAsset:
        """Сохраняет разрешённые документы и изображения после проверки содержимого."""

        if not document_bytes:
            raise ValueError("Content asset file is empty.")
        if len(document_bytes) > self._max_file_size_bytes:
            raise ValueError(
                f"Content asset exceeds the {self._max_file_size_bytes} byte limit.",
            )

        media_type = _detect_media_type(document_bytes)
        normalized_requested_media_type = {
            "image/vnd.microsoft.icon": "image/x-icon",
        }.get(requested_media_type or "", requested_media_type)
        if normalized_requested_media_type and normalized_requested_media_type not in {
            media_type,
            "application/octet-stream",
        }:
            raise ValueError("Declared content type does not match the uploaded file signature.")
        if source_kind not in _ALLOWED_SOURCE_KINDS:
            raise ValueError("Content asset source kind is invalid.")

        safe_file_name = _normalize_file_name(file_name, media_type)
        asset_id = preferred_asset_id or uuid4().hex
        _validate_asset_id(asset_id)
        asset_directory = self._resolve_asset_directory(asset_id)
        payload_path = asset_directory / _PAYLOAD_FILE_NAME
        metadata_path = asset_directory / _METADATA_FILE_NAME
        checksum_sha256 = hashlib.sha256(document_bytes).hexdigest()

        if metadata_path.exists():
            existing_asset = await self.get_asset(asset_id)
            if existing_asset.checksum_sha256 != checksum_sha256:
                raise ValueError("Imported asset id already exists with a different checksum.")
            return existing_asset

        metadata_payload = {
            "assetId": asset_id,
            "fileName": safe_file_name,
            "mediaType": media_type,
            "fileSizeBytes": len(document_bytes),
            "checksumSha256": checksum_sha256,
            "sourceKind": source_kind,
        }
        await asyncio.to_thread(asset_directory.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(payload_path.write_bytes, document_bytes)
        await asyncio.to_thread(
            metadata_path.write_text,
            json.dumps(metadata_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return _map_metadata(metadata_payload)

    async def get_asset(self, asset_id: str) -> StoredContentAsset:
        """Читает и проверяет JSON-метаданные управляемого файла."""

        metadata_path = self._resolve_asset_directory(asset_id) / _METADATA_FILE_NAME
        if not metadata_path.exists():
            raise ContentAssetNotFoundError(f"Content asset '{asset_id}' was not found.")

        metadata_text = await asyncio.to_thread(metadata_path.read_text, encoding="utf-8")
        loaded_metadata = json.loads(metadata_text)
        if not isinstance(loaded_metadata, dict):
            raise ValueError("Content asset metadata must be a JSON object.")
        return _map_metadata(loaded_metadata)

    async def list_assets(self) -> list[StoredContentAsset]:
        """Сканирует только metadata-файлы внутри управляемого storage root."""

        if not self._root_directory.exists():
            return []

        metadata_paths = await asyncio.to_thread(
            lambda: sorted(self._root_directory.glob(f"*/*/{_METADATA_FILE_NAME}")),
        )
        assets: list[StoredContentAsset] = []
        for metadata_path in metadata_paths:
            assets.append(await self.get_asset(metadata_path.parent.name))
        return assets

    async def read_asset_bytes(self, asset_id: str) -> bytes:
        """Читает payload только после проверки существования metadata."""

        await self.get_asset(asset_id)
        payload_path = self._resolve_asset_directory(asset_id) / _PAYLOAD_FILE_NAME
        return await asyncio.to_thread(payload_path.read_bytes)

    async def resolve_asset_path(self, asset_id: str) -> Path:
        """Возвращает путь бинарного payload без возможности выйти за storage root."""

        await self.get_asset(asset_id)
        return self._resolve_asset_directory(asset_id) / _PAYLOAD_FILE_NAME

    async def delete_asset(self, asset_id: str) -> StoredContentAsset:
        """Удаляет каталог одного точного asset id."""

        stored_asset = await self.get_asset(asset_id)
        asset_directory = self._resolve_asset_directory(asset_id)
        await asyncio.to_thread(shutil.rmtree, asset_directory)
        return stored_asset

    def _resolve_asset_directory(self, asset_id: str) -> Path:
        """Нормализует каталог asset и блокирует path traversal."""

        _validate_asset_id(asset_id)
        root_directory = self._root_directory.resolve()
        candidate_path = (root_directory / asset_id[:2] / asset_id).resolve()
        if root_directory not in candidate_path.parents:
            raise ValueError("Content asset path is outside of configured root directory.")
        return candidate_path


def _validate_asset_id(asset_id: str) -> None:
    """Разрешает только UUID-подобные hex-идентификаторы без разделителей."""

    if not _ASSET_ID_PATTERN.fullmatch(asset_id):
        raise ValueError("Content asset id has an invalid format.")


def _detect_media_type(document_bytes: bytes) -> str:
    """Определяет разрешённый тип по сигнатуре, а не по пользовательскому заголовку."""

    if document_bytes.startswith(b"%PDF-"):
        return "application/pdf"
    if document_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if document_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if (
        len(document_bytes) >= 12
        and document_bytes[:4] == b"RIFF"
        and document_bytes[8:12] == b"WEBP"
    ):
        return "image/webp"
    if document_bytes.startswith(b"\x00\x00\x01\x00"):
        return "image/x-icon"
    if _is_safe_svg(document_bytes):
        return "image/svg+xml"
    raise ValueError("Only PDF, JPEG, PNG, WebP, ICO and safe SVG content assets are allowed.")


def _is_safe_svg(document_bytes: bytes) -> bool:
    """Разрешает только автономный SVG без скриптов, внешних ссылок и обработчиков событий."""

    try:
        svg_text = document_bytes.decode("utf-8").lstrip("\ufeff\r\n\t ")
    except UnicodeDecodeError:
        return False
    if not svg_text.startswith("<"):
        return False
    normalized_text = svg_text.lower()
    if "<!doctype" in normalized_text or "<!entity" in normalized_text:
        return False
    try:
        root_element = ElementTree.fromstring(svg_text)
    except ElementTree.ParseError:
        return False
    if _xml_local_name(root_element.tag) != "svg":
        return False
    for element in root_element.iter():
        if _xml_local_name(element.tag) in _FORBIDDEN_SVG_ELEMENTS:
            return False
        for attribute_name, attribute_value in element.attrib.items():
            normalized_name = _xml_local_name(attribute_name)
            normalized_value = attribute_value.strip().lower()
            if normalized_name.startswith("on"):
                return False
            if normalized_name in {"href", "src"} and normalized_value and not normalized_value.startswith("#"):
                return False
            if "url(" in normalized_value:
                return False
    return True


def _xml_local_name(qualified_name: str) -> str:
    """Убирает namespace XML для безопасного сравнения имён SVG."""

    return qualified_name.rsplit("}", 1)[-1].lower()


def _normalize_file_name(file_name: str, media_type: str) -> str:
    """Убирает путь клиента и приводит расширение к проверенному типу файла."""

    normalized_name = (
        Path(file_name).name.strip() or f"document{_SUPPORTED_MEDIA_TYPES[media_type]}"
    )
    expected_extension = _SUPPORTED_MEDIA_TYPES[media_type]
    if Path(normalized_name).suffix.lower() not in {
        expected_extension,
        ".jpeg" if media_type == "image/jpeg" else expected_extension,
    }:
        normalized_name = f"{Path(normalized_name).stem}{expected_extension}"
    return normalized_name


def _map_metadata(metadata_payload: dict[str, object]) -> StoredContentAsset:
    """Преобразует JSON metadata в строгую доменную запись."""

    return StoredContentAsset(
        asset_id=str(metadata_payload["assetId"]),
        file_name=str(metadata_payload["fileName"]),
        media_type=str(metadata_payload["mediaType"]),
        file_size_bytes=int(metadata_payload["fileSizeBytes"]),
        checksum_sha256=str(metadata_payload["checksumSha256"]),
        source_kind=str(metadata_payload.get("sourceKind", "upload")),
    )
