"""Определение форматов входных и выходных документов."""

from __future__ import annotations

import json
from pathlib import Path

from portfolio_cv_importer.domain.constants import (
    PORTFOLIO_BUNDLE_VERSION,
    PORTFOLIO_VERSION,
    SOURCE_FORMAT_PORTFOLIO_BUNDLE,
    SOURCE_FORMAT_PORTFOLIO_JSON,
    SOURCE_FORMAT_RESUME_HTML,
    SOURCE_FORMAT_RESUME_MARKDOWN,
    SOURCE_FORMAT_RESUME_PDF,
    SOURCE_FORMAT_RESUME_TEXT,
    TARGET_FORMAT_PORTFOLIO_BUNDLE,
    TARGET_FORMAT_PORTFOLIO_JSON,
    TARGET_FORMAT_RESUME_MARKDOWN,
)
from portfolio_cv_importer.errors import (
    InvalidPortfolioDocumentError,
    UnsupportedSourceFormatError,
    UnsupportedTargetFormatError,
)


def detect_source_format(source_file_name: str, source_bytes: bytes) -> str:
    """Определяет формат входного документа по расширению и, если нужно, по содержимому."""

    source_extension = Path(source_file_name).suffix.lower()
    if source_extension == ".pdf":
        return SOURCE_FORMAT_RESUME_PDF

    if source_extension in {".md", ".markdown"}:
        return SOURCE_FORMAT_RESUME_MARKDOWN

    if source_extension in {".txt", ".text"}:
        return SOURCE_FORMAT_RESUME_TEXT

    if source_extension in {".html", ".htm"}:
        return SOURCE_FORMAT_RESUME_HTML

    if source_extension == ".json":
        return detect_json_document_format(source_bytes)

    raise UnsupportedSourceFormatError(source_file_name)


def detect_json_document_format(source_bytes: bytes) -> str:
    """Определяет, является ли JSON raw `portfolio.v1` или bundle-документом."""

    try:
        parsed_document = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidPortfolioDocumentError("JSON document could not be decoded as UTF-8 portfolio payload.") from error

    if not isinstance(parsed_document, dict):
        raise InvalidPortfolioDocumentError("JSON portfolio document must be an object.")

    if parsed_document.get("version") == PORTFOLIO_VERSION:
        return SOURCE_FORMAT_PORTFOLIO_JSON

    if parsed_document.get("bundleVersion") == PORTFOLIO_BUNDLE_VERSION or isinstance(parsed_document.get("snapshot"), dict):
        return SOURCE_FORMAT_PORTFOLIO_BUNDLE

    raise InvalidPortfolioDocumentError("Provided JSON document is neither a portfolio bundle nor a raw portfolio.v1 payload.")


def detect_target_format(target_path: Path, explicit_target_format: str | None = None) -> str:
    """Определяет формат выходного документа по аргументу или расширению."""

    if explicit_target_format:
        if explicit_target_format in {
            TARGET_FORMAT_PORTFOLIO_JSON,
            TARGET_FORMAT_PORTFOLIO_BUNDLE,
            TARGET_FORMAT_RESUME_MARKDOWN,
        }:
            return explicit_target_format
        raise UnsupportedTargetFormatError(explicit_target_format)

    target_extension = target_path.suffix.lower()
    if target_extension == ".json":
        return TARGET_FORMAT_PORTFOLIO_JSON

    if target_extension in {".md", ".markdown"}:
        return TARGET_FORMAT_RESUME_MARKDOWN

    if target_extension == ".bundle":
        return TARGET_FORMAT_PORTFOLIO_BUNDLE

    raise UnsupportedTargetFormatError(target_path.name)
