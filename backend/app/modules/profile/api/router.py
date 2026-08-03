"""Router модуля profile."""

from fastapi import APIRouter, Query

from app.modules.profile.api.responses import PublicProfileResponse
from app.modules.profile.application.service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])

profile_service = ProfileService()


@router.get("", response_model=PublicProfileResponse)
async def get_public_profile(
    locale: str = Query(default="en", pattern="^(ru|en)$"),
) -> PublicProfileResponse:
    """Возвращает публичный профиль для hero-экрана."""

    profile_payload = await profile_service.get_public_profile(locale_code=locale)
    return PublicProfileResponse.model_validate(profile_payload)

