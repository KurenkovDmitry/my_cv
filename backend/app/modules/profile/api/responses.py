"""Response-модели модуля profile."""

from pydantic import BaseModel, Field


class PublicProfileResponse(BaseModel):
    """Ответ публичного профиля."""

    display_name: str = Field(alias="displayName")
    headline: str
    summary: str

