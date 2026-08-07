"""Доменные модели import/export контура."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class SourceDocument:
    """Входной документ импорта в одном из поддерживаемых форматов."""

    source_path: Path
    source_format: str
    source_bytes: bytes


@dataclass(slots=True, frozen=True)
class TargetDocument:
    """Целевой документ экспорта."""

    target_path: Path
    target_format: str


@dataclass(slots=True, frozen=True)
class ResumeEntry:
    """Склеенный пункт резюме после нормализации строк."""

    text: str
    period: str
    lines: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ResumeSections:
    """Секции резюме после грубого структурного разбора."""

    location_ru: str
    location_en: str
    education_lines: list[str]
    experience_lines: list[str]
    project_lines: list[str]
    study_project_lines: list[str]
    header_lines: list[str] = field(default_factory=list)
    section_lines: dict[str, list[str]] = field(default_factory=dict)
    detected_layout: str = "unstructured"


@dataclass(slots=True, frozen=True)
class ConversionResult:
    """Результат нормализации входного документа в `portfolio.v1`."""

    payload: dict[str, Any]
    source_format: str
    warnings: list[str]
