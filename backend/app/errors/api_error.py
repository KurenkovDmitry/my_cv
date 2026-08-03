"""Общие типы ошибок API."""

from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    """Стабильный DTO для ошибок API."""

    code: str = Field(description="Машиночитаемый код ошибки.")
    message: str = Field(description="Понятное человеку описание ошибки.")
    details: dict[str, str | int | bool] = Field(default_factory=dict)
    trace_id: str | None = Field(default=None, alias="traceId")

