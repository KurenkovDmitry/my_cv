"""Pydantic-модели ответа административной аутентификации."""

from pydantic import BaseModel, Field


class AdminSessionResponse(BaseModel):
    """Снимок текущей административной сессии для frontend-панели."""

    login: str
    expires_at: str = Field(alias="expiresAt")
    csrf_token: str = Field(alias="csrfToken")
