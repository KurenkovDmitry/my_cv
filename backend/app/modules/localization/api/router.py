"""Router модуля localization."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/localization", tags=["localization"])


class LocalizationConfigResponse(BaseModel):
    """Публичная конфигурация локализации."""

    default_locale: str
    supported_locales: list[str]


@router.get("", response_model=LocalizationConfigResponse)
async def get_localization_config() -> LocalizationConfigResponse:
    """Возвращает список поддерживаемых локалей."""

    return LocalizationConfigResponse(
        default_locale="en",
        supported_locales=["en", "ru"],
    )

