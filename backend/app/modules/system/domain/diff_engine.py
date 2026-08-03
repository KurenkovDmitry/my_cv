"""Контракты compare/diff engine для backup и import candidate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class ContentDiffRecord:
    """Компактная summary diff-структура для админки."""

    left_label: str
    right_label: str
    changed_paths: list[str]
    sections: list[str]
    changed_paths_count: int
    sections_changed_count: int


class ContentDiffEngine(Protocol):
    """Фасад compare-движка поверх native Python/C++ библиотеки."""

    async def compare(
        self,
        *,
        left_payload: dict[str, object],
        right_payload: dict[str, object],
        left_label: str,
        right_label: str,
    ) -> ContentDiffRecord:
        """Сравнивает два документа и возвращает JSON-friendly summary diff."""
