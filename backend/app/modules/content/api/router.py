"""Router snapshot-модуля контента."""

from html import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse

from app.config.settings import Settings, get_settings
from app.modules.content.api.dependencies import get_content_service
from app.modules.content.api.responses import PublicPortfolioResponse
from app.modules.content.application.service import ContentService
from app.modules.content.domain.asset_storage import ContentAssetStorage
from app.modules.content.infrastructure.dependencies import get_content_asset_storage
from app.modules.content.infrastructure.local_asset_storage import ContentAssetNotFoundError

router = APIRouter(prefix="/portfolio", tags=["content"])
_LEGACY_PROFILE_ASSET_ID = "e6b61031e7c24de94cfb70f4b645c989"
_DEFAULT_SOCIAL_PREVIEW_ASSET_ID = "5a12d533e165b0e81a4ab7f3d35ef58"
_DEFAULT_FAVICON_ASSET_ID = "2de32610b8a3807476da3c26635ed06d"


@router.get("", response_model=PublicPortfolioResponse)
async def get_public_portfolio(
    content_service: ContentService = Depends(get_content_service),
) -> PublicPortfolioResponse:
    """Возвращает единый опубликованный snapshot портфолио для SSR и гидратации."""

    snapshot = await content_service.get_public_snapshot()
    return PublicPortfolioResponse(
        snapshotKind=snapshot.snapshot_kind,
        contentSchemaVersion=snapshot.content_schema_version,
        contentChecksumSha256=snapshot.content_checksum_sha256,
        updatedAt=snapshot.updated_at,
        payload=snapshot.payload,
    )


@router.get("/social-meta", response_class=HTMLResponse, include_in_schema=False)
async def get_social_meta_fragment(
    settings: Settings = Depends(get_settings),
    content_service: ContentService = Depends(get_content_service),
    asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> HTMLResponse:
    """Отдаёт актуальные Open Graph-теги для Nginx SSI без выполнения JavaScript."""

    snapshot = await content_service.get_public_snapshot()
    seo = _as_object(snapshot.payload.get("seo"))
    profile = _as_object(snapshot.payload.get("profile"))
    title = _localized_text(
        seo.get("shareTitle"),
        fallback=f"{_localized_text(profile.get('displayName'), 'Дмитрий Куренков')} — системный аналитик",
    )
    description = _localized_text(
        seo.get("shareDescription"),
        fallback=_localized_text(profile.get("summary"), "Портфолио системного аналитика."),
    )
    site_name = _localized_text(seo.get("siteName"), "Портфолио Дмитрия Куренкова")
    origin = settings.public_frontend_origin.rstrip("/")
    version = snapshot.content_checksum_sha256[:16]
    image_url = f"{origin}/api/public/portfolio/social-preview?v={version}"
    favicon_url = f"{origin}/api/public/portfolio/favicon?v={version}"
    canonical_url = f"{origin}/"
    configured_asset_id = _configured_asset_id(
        seo,
        field_name="openGraphAssetId",
        default_asset_id=_DEFAULT_SOCIAL_PREVIEW_ASSET_ID,
    )
    stored_asset_id = await _available_asset_id(
        asset_storage,
        configured_asset_id,
        _DEFAULT_SOCIAL_PREVIEW_ASSET_ID,
    )
    stored_asset = await asset_storage.get_asset(stored_asset_id)

    meta_tags = [
        _meta_name("description", description),
        f'<link rel="canonical" href="{escape(canonical_url, quote=True)}" />',
        f'<link rel="icon" href="{escape(favicon_url, quote=True)}" />',
        _meta_property("og:type", "profile"),
        _meta_property("og:url", canonical_url),
        _meta_property("og:site_name", site_name),
        _meta_property("og:locale", "ru_RU"),
        _meta_property("og:locale:alternate", "en_US"),
        _meta_property("og:title", title),
        _meta_property("og:description", description),
        _meta_property("og:image", image_url),
        _meta_property("og:image:secure_url", image_url),
        _meta_property("og:image:type", stored_asset.media_type),
        _meta_property("og:image:alt", "Дмитрий Куренков — системный аналитик"),
    ]
    if stored_asset_id == _DEFAULT_SOCIAL_PREVIEW_ASSET_ID:
        meta_tags.extend(
            [
                _meta_property("og:image:width", "1200"),
                _meta_property("og:image:height", "630"),
            ]
        )
    meta_tags.extend(
        [
            _meta_name("twitter:card", "summary_large_image"),
            _meta_name("twitter:title", title),
            _meta_name("twitter:description", description),
            _meta_name("twitter:image", image_url),
            _meta_name("twitter:image:alt", "Дмитрий Куренков — системный аналитик"),
        ]
    )
    return HTMLResponse(
        content="\n".join(meta_tags),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/social-preview", include_in_schema=False)
async def download_social_preview(
    content_service: ContentService = Depends(get_content_service),
    asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> FileResponse:
    """Отдаёт выбранное в админке social-изображение по стабильному публичному URL."""

    snapshot = await content_service.get_public_snapshot()
    seo = _as_object(snapshot.payload.get("seo"))
    configured_asset_id = _configured_asset_id(
        seo,
        field_name="openGraphAssetId",
        default_asset_id=_DEFAULT_SOCIAL_PREVIEW_ASSET_ID,
    )
    return await _asset_file_response(
        asset_storage,
        configured_asset_id,
        _DEFAULT_SOCIAL_PREVIEW_ASSET_ID,
    )


@router.get("/favicon", include_in_schema=False)
async def download_public_favicon(
    content_service: ContentService = Depends(get_content_service),
    asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> FileResponse:
    """Отдаёт выбранный favicon и безопасный анимированный SVG по умолчанию."""

    snapshot = await content_service.get_public_snapshot()
    seo = _as_object(snapshot.payload.get("seo"))
    configured_asset_id = _configured_asset_id(
        seo,
        field_name="faviconAssetId",
        default_asset_id=_DEFAULT_FAVICON_ASSET_ID,
    )
    return await _asset_file_response(
        asset_storage,
        configured_asset_id,
        _DEFAULT_FAVICON_ASSET_ID,
    )


@router.get("/assets/{asset_id}")
async def download_public_content_asset(
    asset_id: str,
    asset_storage: ContentAssetStorage = Depends(get_content_asset_storage),
) -> FileResponse:
    """Отдаёт только разрешённые управляемые файлы по непрогнозируемому asset id."""

    try:
        stored_asset = await asset_storage.get_asset(asset_id)
        asset_path = await asset_storage.resolve_asset_path(asset_id)
    except (ContentAssetNotFoundError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return FileResponse(
        path=asset_path,
        filename=stored_asset.file_name,
        media_type=stored_asset.media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def _as_object(value: object) -> dict[str, object]:
    """Безопасно приводит JSON-узел snapshot к объекту."""

    return value if isinstance(value, dict) else {}


def _localized_text(value: object, fallback: str) -> str:
    """Выбирает русскую, затем английскую строку локализованного поля."""

    if isinstance(value, dict):
        for locale_code in ("ru", "en"):
            localized_value = value.get(locale_code)
            if isinstance(localized_value, str) and localized_value.strip():
                return localized_value.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _configured_asset_id(
    seo: dict[str, object],
    *,
    field_name: str,
    default_asset_id: str,
) -> str:
    """Использует новый выбранный asset, заменяя старую фотографию-дефолт."""

    configured_asset_id = seo.get(field_name)
    if not isinstance(configured_asset_id, str) or configured_asset_id == _LEGACY_PROFILE_ASSET_ID:
        return default_asset_id
    return configured_asset_id or default_asset_id


async def _available_asset_id(
    asset_storage: ContentAssetStorage,
    requested_asset_id: str,
    fallback_asset_id: str,
) -> str:
    """Возвращает существующий asset id либо id встроенного fallback."""

    try:
        await asset_storage.get_asset(requested_asset_id)
        return requested_asset_id
    except (ContentAssetNotFoundError, ValueError):
        await asset_storage.get_asset(fallback_asset_id)
        return fallback_asset_id


async def _asset_file_response(
    asset_storage: ContentAssetStorage,
    requested_asset_id: str,
    fallback_asset_id: str,
) -> FileResponse:
    """Строит публичный ответ для изменяемого через админку изображения."""

    asset_id = await _available_asset_id(asset_storage, requested_asset_id, fallback_asset_id)
    stored_asset = await asset_storage.get_asset(asset_id)
    asset_path = await asset_storage.resolve_asset_path(asset_id)
    return FileResponse(
        path=asset_path,
        media_type=stored_asset.media_type,
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=86400"},
    )


def _meta_property(property_name: str, content: str) -> str:
    """Формирует экранированный Open Graph meta-тег."""

    return (
        f'<meta property="{escape(property_name, quote=True)}" '
        f'content="{escape(content, quote=True)}" />'
    )


def _meta_name(name: str, content: str) -> str:
    """Формирует экранированный обычный meta-тег."""

    return f'<meta name="{escape(name, quote=True)}" content="{escape(content, quote=True)}" />'
