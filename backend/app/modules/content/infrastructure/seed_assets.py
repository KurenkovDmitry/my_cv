"""Идемпотентная загрузка исходных документов резюме в управляемый storage."""

from __future__ import annotations

import asyncio
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
        )
