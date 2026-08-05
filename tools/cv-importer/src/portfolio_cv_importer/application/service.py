"""Application-сервис import/export контура."""

from __future__ import annotations

import json
from typing import Any

from portfolio_cv_importer.application.commands import (
    ConvertSourceToPortfolioCommand,
    ExportPortfolioDocumentCommand,
)
from portfolio_cv_importer.domain.constants import (
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
from portfolio_cv_importer.domain.models import ConversionResult
from portfolio_cv_importer.errors import (
    InvalidPortfolioDocumentError,
    UnsupportedSourceFormatError,
    UnsupportedTargetFormatError,
)
from portfolio_cv_importer.exporters.portfolio_document_exporter import (
    export_portfolio_bundle,
    export_portfolio_json,
    export_resume_markdown,
)
from portfolio_cv_importer.extractors.native_pdf_extractor import extract_lines_from_pdf_with_optional_native_bridge
from portfolio_cv_importer.format_detection import detect_source_format, detect_target_format
from portfolio_cv_importer.normalizers.text_normalizer import normalize_resume_source_lines
from portfolio_cv_importer.parsers.resume_portfolio_mapper import build_portfolio_payload_from_resume_sections
from portfolio_cv_importer.parsers.resume_section_parser import split_resume_sections


class CvImportExportService:
    """Оркестрирует import/export между resume-like документами и `portfolio.v1`."""

    def convert_source_to_portfolio(self, command: ConvertSourceToPortfolioCommand) -> ConversionResult:
        """Конвертирует входной документ в raw `portfolio.v1` и записывает JSON на диск."""

        source_bytes = command.source_path.read_bytes()
        source_format = detect_source_format(command.source_path.name, source_bytes)
        conversion_result = self.convert_source_bytes_to_portfolio(
            source_file_name=command.source_path.name,
            source_bytes=source_bytes,
            source_format=source_format,
        )
        command.target_path.parent.mkdir(parents=True, exist_ok=True)
        command.target_path.write_text(
            export_portfolio_json(conversion_result.payload),
            encoding="utf-8",
        )
        return conversion_result

    def convert_source_bytes_to_portfolio(
        self,
        *,
        source_file_name: str,
        source_bytes: bytes,
        source_format: str | None = None,
    ) -> ConversionResult:
        """Конвертирует байты входного документа в нормализованный `portfolio.v1`."""

        resolved_source_format = source_format or detect_source_format(source_file_name, source_bytes)

        if resolved_source_format in {SOURCE_FORMAT_PORTFOLIO_JSON, SOURCE_FORMAT_PORTFOLIO_BUNDLE}:
            payload = extract_portfolio_payload_from_json_bytes(source_bytes)
            warnings = build_warning_messages(payload)
            return ConversionResult(payload=payload, source_format=resolved_source_format, warnings=warnings)

        if resolved_source_format == SOURCE_FORMAT_RESUME_PDF:
            extracted_lines = extract_lines_from_pdf_with_optional_native_bridge(source_bytes)
            payload = build_portfolio_payload_from_resume_sections(split_resume_sections(extracted_lines))
            warnings = build_warning_messages(payload)
            return ConversionResult(payload=payload, source_format=resolved_source_format, warnings=warnings)

        if resolved_source_format in {
            SOURCE_FORMAT_RESUME_MARKDOWN,
            SOURCE_FORMAT_RESUME_TEXT,
            SOURCE_FORMAT_RESUME_HTML,
        }:
            raw_text = source_bytes.decode("utf-8")
            normalized_lines = normalize_resume_source_lines(raw_text)
            payload = build_portfolio_payload_from_resume_sections(split_resume_sections(normalized_lines))
            warnings = build_warning_messages(payload)
            return ConversionResult(payload=payload, source_format=resolved_source_format, warnings=warnings)

        raise UnsupportedSourceFormatError(source_file_name)

    def export_portfolio_document(self, command: ExportPortfolioDocumentCommand) -> str:
        """Экспортирует `portfolio.v1` в требуемый выходной формат и сохраняет результат на диск."""

        payload = extract_portfolio_payload_from_json_bytes(command.source_path.read_bytes())
        target_format = detect_target_format(command.target_path, command.target_format)

        if target_format == TARGET_FORMAT_PORTFOLIO_JSON:
            rendered_document = export_portfolio_json(payload)
        elif target_format == TARGET_FORMAT_PORTFOLIO_BUNDLE:
            rendered_document = export_portfolio_bundle(payload)
        elif target_format == TARGET_FORMAT_RESUME_MARKDOWN:
            rendered_document = export_resume_markdown(payload)
        else:
            raise UnsupportedTargetFormatError(target_format)

        command.target_path.parent.mkdir(parents=True, exist_ok=True)
        command.target_path.write_text(rendered_document, encoding="utf-8")
        return rendered_document


def extract_portfolio_payload_from_json_bytes(document_bytes: bytes) -> dict[str, Any]:
    """Извлекает `portfolio.v1` payload из raw документа или bundle."""

    try:
        parsed_document = json.loads(document_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidPortfolioDocumentError("JSON document could not be decoded as UTF-8 portfolio payload.") from error

    if not isinstance(parsed_document, dict):
        raise InvalidPortfolioDocumentError("Portfolio document must be a JSON object.")

    snapshot_block = parsed_document.get("snapshot")
    if isinstance(snapshot_block, dict):
        nested_payload = snapshot_block.get("payload")
        if isinstance(nested_payload, dict):
            return dict(nested_payload)

    version = parsed_document.get("version")
    if version == "portfolio.v1":
        return dict(parsed_document)

    raise InvalidPortfolioDocumentError("Provided JSON document is neither a portfolio bundle nor a raw portfolio.v1 payload.")


def build_warning_messages(candidate_payload: dict[str, object]) -> list[str]:
    """Возвращает предупреждения по импортируемому payload."""

    warning_messages: list[str] = []
    if candidate_payload.get("needsManualReview") is True:
        warning_messages.append("Candidate payload still requests manual review.")
    return warning_messages
