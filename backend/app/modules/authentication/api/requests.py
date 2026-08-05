"""Pydantic-модели запроса административной аутентификации."""

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    """Запрос входа в административную панель по логину и паролю из `.env`."""

    login: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=4096)
