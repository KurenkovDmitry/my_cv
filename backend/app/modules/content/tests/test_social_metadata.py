"""Тесты серверных метаданных карточки общей ссылки."""

from types import SimpleNamespace

import pytest

from app.config.settings import Settings
from app.modules.content.api.router import get_social_meta_fragment


class _ContentServiceStub:
    async def get_public_snapshot(self) -> SimpleNamespace:
        return SimpleNamespace(
            content_checksum_sha256="abcdef1234567890abcdef1234567890",
            payload={
                "profile": {
                    "displayName": {"ru": "Дмитрий Куренков", "en": "Dmitry Kurenkov"},
                    "summary": {"ru": "Портфолио системного аналитика.", "en": "Portfolio."},
                },
                "seo": {
                    "siteName": {"ru": "Портфолио Дмитрия Куренкова", "en": "Portfolio"},
                    "shareTitle": {"ru": "Дмитрий Куренков — системный аналитик"},
                    "shareDescription": {"ru": "Highload, данные и архитектура."},
                    "openGraphAssetId": "5a12d533e165b0e81a4ab7f3d35ef58",
                },
            },
        )


class _AssetStorageStub:
    async def get_asset(self, asset_id: str) -> SimpleNamespace:
        assert asset_id == "5a12d533e165b0e81a4ab7f3d35ef58"
        return SimpleNamespace(media_type="image/png")


@pytest.mark.asyncio
async def test_social_meta_uses_absolute_versioned_urls_and_published_copy() -> None:
    response = await get_social_meta_fragment(
        settings=Settings(PUBLIC_FRONTEND_ORIGIN="https://portfolio.example"),
        content_service=_ContentServiceStub(),  # type: ignore[arg-type]
        asset_storage=_AssetStorageStub(),  # type: ignore[arg-type]
    )

    response_body = response.body.decode("utf-8")
    assert 'property="og:title" content="Дмитрий Куренков — системный аналитик"' in response_body
    assert 'property="og:image:width" content="1200"' in response_body
    assert "https://portfolio.example/api/public/portfolio/social-preview?v=abcdef1234567890" in response_body
    assert "https://portfolio.example/api/public/portfolio/favicon?v=abcdef1234567890" in response_body
