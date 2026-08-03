"""Контрактная заготовка Redis-кэша модуля projects."""


class ProjectCacheFacade:
    """Фасад кэша.

    Реальная реализация появится после подключения Redis client и TTL-конфигурации.
    """

    async def get_featured(self, locale_code: str) -> None:
        return None

    async def set_featured(self, locale_code: str, payload: object, ttl_seconds: int) -> None:
        _ = locale_code
        _ = payload
        _ = ttl_seconds

