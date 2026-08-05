"""Application-команды import/export контура."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ConvertSourceToPortfolioCommand:
    """Команда конвертации исходного документа в raw `portfolio.v1`."""

    source_path: Path
    target_path: Path


@dataclass(slots=True, frozen=True)
class ExportPortfolioDocumentCommand:
    """Команда экспорта `portfolio.v1` в bundle или resume-like формат."""

    source_path: Path
    target_path: Path
    target_format: str | None = None
