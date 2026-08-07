"""Тесты переносимого файлового контура резюме."""

import hashlib
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.modules.content.application.asset_bundle import (
    build_asset_bundle_entries,
    collect_referenced_asset_ids,
    restore_bundled_assets,
)
from app.modules.content.infrastructure.local_asset_storage import LocalContentAssetStorage
from app.modules.content.infrastructure.seed_assets import _SEED_ASSETS

_MINIMAL_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


def test_seed_asset_ids_match_bundled_file_checksums() -> None:
    """Не допускает невалидные или рассинхронизированные id встроенных файлов."""

    seed_root = Path(__file__).resolve().parents[3] / "seed_assets"
    for file_name, asset_id, _media_type in _SEED_ASSETS:
        document_bytes = (seed_root / file_name).read_bytes()
        assert asset_id == hashlib.sha256(document_bytes).hexdigest()[:32]


def _build_storage(root_directory: Path) -> LocalContentAssetStorage:
    """Создаёт изолированное файловое хранилище для одного теста."""

    settings = Settings(
        CONTENT_ASSET_STORAGE_PATH=str(root_directory),
        CONTENT_ASSET_MAX_BYTES=1024 * 1024,
    )
    return LocalContentAssetStorage(settings)


@pytest.mark.asyncio
async def test_asset_is_embedded_and_restored_with_stable_identifier(tmp_path: Path) -> None:
    """Проверяет, что backup переносит PDF и сохраняет ссылочный asset id."""

    source_storage = _build_storage(tmp_path / "source-assets")
    target_storage = _build_storage(tmp_path / "target-assets")
    stored_asset = await source_storage.write_asset(
        file_name="certificate.pdf",
        document_bytes=_MINIMAL_PDF_BYTES,
        requested_media_type="application/pdf",
    )
    portfolio_payload = {
        "profile": {"avatarAssetId": ""},
        "skills": {"proofs": [{"assetId": stored_asset.asset_id}]},
    }

    assert collect_referenced_asset_ids(portfolio_payload) == [stored_asset.asset_id]
    bundle_entries = await build_asset_bundle_entries(portfolio_payload, source_storage)
    restored_asset_ids = await restore_bundled_assets(bundle_entries, target_storage)

    assert restored_asset_ids == [stored_asset.asset_id]
    restored_asset = await target_storage.get_asset(stored_asset.asset_id)
    assert restored_asset.checksum_sha256 == stored_asset.checksum_sha256
    assert await target_storage.read_asset_bytes(stored_asset.asset_id) == _MINIMAL_PDF_BYTES


@pytest.mark.asyncio
async def test_asset_storage_rejects_executable_payload(tmp_path: Path) -> None:
    """Проверяет запрет произвольных файлов даже при безопасном имени PDF."""

    asset_storage = _build_storage(tmp_path / "assets")
    with pytest.raises(ValueError, match="Only PDF, JPEG"):
        await asset_storage.write_asset(
            file_name="fake.pdf",
            document_bytes=b"MZ-not-a-pdf",
            requested_media_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_asset_storage_accepts_safe_svg_and_marks_source_kind(tmp_path: Path) -> None:
    """Проверяет безопасные встроенные SVG без скриптов и внешних ресурсов."""

    asset_storage = _build_storage(tmp_path / "assets")
    stored_asset = await asset_storage.write_asset(
        file_name="avatar.svg",
        document_bytes=b'<svg xmlns="http://www.w3.org/2000/svg"><circle cx="5" cy="5" r="5"/></svg>',
        requested_media_type="image/svg+xml",
        source_kind="custom_avatar",
    )

    assert stored_asset.media_type == "image/svg+xml"
    assert stored_asset.source_kind == "custom_avatar"


@pytest.mark.asyncio
async def test_asset_storage_rejects_active_svg(tmp_path: Path) -> None:
    """Не допускает SVG со скриптом даже при корректном MIME-типе."""

    asset_storage = _build_storage(tmp_path / "assets")
    with pytest.raises(ValueError, match="safe SVG"):
        await asset_storage.write_asset(
            file_name="unsafe.svg",
            document_bytes=b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            requested_media_type="image/svg+xml",
        )
