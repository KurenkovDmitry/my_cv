"""Идемпотентная загрузка исходных документов резюме в управляемый storage."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from app.modules.content.domain.asset_storage import ContentAssetStorage

_SEED_ASSETS: tuple[tuple[str, str, str], ...] = (
    ("certificate-api-advanced.pdf", "b4e9d13a6ae57263ee6b3ca8dd2020b3", "application/pdf"),
    ("certificate-docker-intermediate.pdf", "4c10e2659d4679cbae13d7b76c5453f9", "application/pdf"),
    ("certificate-git-intermediate.pdf", "6f8adacfff063deee47a280697dd9106", "application/pdf"),
    (
        "certificate-javascript-intermediate.pdf",
        "ff43482301dea9a0fa9a77a1d4125abd",
        "application/pdf",
    ),
    (
        "certificate-postgresql-intermediate.pdf",
        "f04d7ef2663f6f141d9d352e8fa4bb7c",
        "application/pdf",
    ),
    (
        "diploma-vk-technopark-web-development.pdf",
        "f2c55f2afcbe9d11b7de2aec3d13fc48",
        "application/pdf",
    ),
    ("photo_2025-04-09_22-18-09.jpg", "e6b61031e7c24de94cfb70f4b645c989", "image/jpeg"),
    ("social-preview-v1.png", "5a12d533e165b0e81a4ab7f3d35ef58a", "image/png"),
    (
        "favicon-blueprint-animated.svg",
        "2de32610b8a3807476da3c26635ed06d",
        "image/svg+xml",
    ),
)


async def seed_initial_content_assets(asset_storage: ContentAssetStorage) -> None:
    """Копирует bundled документы в volume только при отсутствии соответствующего asset id."""

    seed_root = Path(__file__).resolve().parents[3] / "seed_assets"
    for file_name, asset_id, media_type in _SEED_ASSETS:
        try:
            await asset_storage.get_asset(asset_id)
            continue
        except FileNotFoundError:
            pass

        source_path = seed_root / file_name
        document_bytes = await asyncio.to_thread(source_path.read_bytes)
        await asset_storage.write_asset(
            file_name=file_name,
            document_bytes=document_bytes,
            requested_media_type=media_type,
            preferred_asset_id=asset_id,
            source_kind="seed",
        )

    custom_avatar_root = _find_custom_avatar_root()
    if custom_avatar_root is None:
        return
    for source_path in sorted(custom_avatar_root.glob("*.svg")):
        avatar_asset_id = hashlib.sha256(
            f"portfolio-custom-avatar:{source_path.name}".encode("utf-8"),
        ).hexdigest()[:32]
        try:
            await asset_storage.get_asset(avatar_asset_id)
            continue
        except FileNotFoundError:
            pass
        avatar_bytes = await asyncio.to_thread(source_path.read_bytes)
        await asset_storage.write_asset(
            file_name=source_path.name,
            document_bytes=avatar_bytes,
            requested_media_type="image/svg+xml",
            preferred_asset_id=avatar_asset_id,
            source_kind="custom_avatar",
        )


def _find_custom_avatar_root() -> Path | None:
    """Находит каталог аватаров и в checkout, и внутри Docker-образа backend."""

    module_path = Path(__file__).resolve()
    candidates = (
        module_path.parents[3] / "custom_avatars",
        module_path.parents[5] / "rules" / "custom avatars",
    )
    return next((candidate for candidate in candidates if candidate.is_dir()), None)
