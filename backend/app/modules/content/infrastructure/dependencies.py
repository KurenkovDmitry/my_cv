"""Dependency-фабрики инфраструктуры управляемых файлов контента."""

from functools import lru_cache

from app.config.settings import get_settings
from app.modules.content.domain.asset_storage import ContentAssetStorage
from app.modules.content.infrastructure.local_asset_storage import LocalContentAssetStorage


@lru_cache(maxsize=1)
def get_content_asset_storage() -> ContentAssetStorage:
    """Возвращает singleton-фасад управляемого хранилища файлов портфолио."""

    return LocalContentAssetStorage(settings=get_settings())
