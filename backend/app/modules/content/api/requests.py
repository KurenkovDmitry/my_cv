"""Request-модели mutation-path контентной админки."""

from typing import Any

from pydantic import BaseModel


class DraftSnapshotUpsertRequest(BaseModel):
    """Тело запроса на сохранение текущего draft snapshot."""

    payload: dict[str, Any]
