"""Доменные сущности модуля profile."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PublicProfile:
    """Публичный профиль владельца портфолио."""

    display_name_ru: str
    display_name_en: str
    headline_ru: str
    headline_en: str
    summary_ru: str
    summary_en: str

