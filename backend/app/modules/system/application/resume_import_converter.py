"""Адаптер конвертации resume-like документов в `portfolio.v1`."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.config.settings import Settings
from app.modules.content.application.asset_bundle import extract_bundled_assets
from app.modules.system.application.bundle_payloads import extract_portfolio_payload


class ResumeImportConverter:
    """Нормализует входной документ в raw `portfolio.v1` через Python CLI и optional C++ PDF extractor."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def convert_to_portfolio_payload(
        self,
        *,
        source_file_name: str,
        document_bytes: bytes,
    ) -> tuple[dict[str, object], str, list[dict[str, object]]]:
        """Конвертирует документ в payload, тип источника и переносимые asset-записи."""

        source_kind = self._detect_source_kind(source_file_name)
        if source_kind == "json_document":
            parsed_document = json.loads(document_bytes.decode("utf-8"))
            if not isinstance(parsed_document, dict):
                raise ValueError("Import candidate JSON document must be an object.")

            return (
                extract_portfolio_payload(parsed_document),
                self._detect_json_source_kind(parsed_document),
                extract_bundled_assets(parsed_document),
            )

        converted_payload, converted_source_kind = await asyncio.to_thread(
            self._convert_resume_document,
            source_file_name,
            document_bytes,
            source_kind,
        )
        return converted_payload, converted_source_kind, []

    def _convert_resume_document(
        self,
        source_file_name: str,
        document_bytes: bytes,
        source_kind: str,
    ) -> tuple[dict[str, object], str]:
        """Запускает внешний Python CLI конвертации и читает нормализованный JSON-результат."""

        if not self._settings.resume_import_python_binary.strip():
            raise ValueError("RESUME_IMPORT_PYTHON_BINARY must not be blank.")

        if not self._settings.resume_import_cli_module.strip():
            raise ValueError("RESUME_IMPORT_CLI_MODULE must not be blank.")

        with tempfile.TemporaryDirectory(prefix="portfolio-resume-import-") as temporary_directory:
            temporary_root = Path(temporary_directory)
            source_path = temporary_root / source_file_name
            target_path = temporary_root / f"{Path(source_file_name).stem}.portfolio.v1.json"
            source_path.write_bytes(document_bytes)

            completed_process = subprocess.run(
                [
                    self._settings.resume_import_python_binary,
                    "-m",
                    self._settings.resume_import_cli_module,
                    str(source_path),
                    str(target_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=self._resolve_workdir(),
                env=self._build_process_environment(),
            )

            if not target_path.exists():
                stderr_output = completed_process.stderr.strip() or "no stderr"
                raise ValueError(f"Resume importer did not produce target JSON file: {stderr_output}.")

            parsed_document = json.loads(target_path.read_text(encoding="utf-8"))
            if not isinstance(parsed_document, dict):
                raise ValueError("Resume importer must produce a JSON object.")

        return extract_portfolio_payload(parsed_document), source_kind

    def _build_process_environment(self) -> dict[str, str]:
        """Собирает окружение subprocess для Python importer и optional native PDF binary."""

        process_environment = dict(os.environ)

        if self._settings.resume_import_pythonpath.strip():
            resolved_pythonpath = str(self._resolve_relative_path(self._settings.resume_import_pythonpath))
            current_pythonpath = process_environment.get("PYTHONPATH", "").strip()
            process_environment["PYTHONPATH"] = (
                f"{resolved_pythonpath}{os.pathsep}{current_pythonpath}" if current_pythonpath else resolved_pythonpath
            )

        if self._settings.resume_import_native_pdf_binary.strip():
            process_environment["PORTFOLIO_RESUME_NATIVE_PDF_BINARY"] = str(
                self._resolve_relative_path(self._settings.resume_import_native_pdf_binary),
            )

        return process_environment

    def _resolve_workdir(self) -> str:
        """Возвращает рабочую директорию запуска importer subprocess."""

        return str(self._resolve_relative_path(self._settings.resume_import_workdir))

    def _resolve_relative_path(self, configured_path: str) -> Path:
        """Нормализует путь относительно корня текущего workspace."""

        candidate_path = Path(configured_path)
        if candidate_path.is_absolute():
            return candidate_path

        return (Path.cwd() / candidate_path).resolve()

    def _detect_source_kind(self, source_file_name: str) -> str:
        """Определяет тип источника по расширению и, при необходимости, по содержимому."""

        source_extension = Path(source_file_name).suffix.lower()
        if source_extension == ".pdf":
            return "resume_pdf"

        if source_extension in {".md", ".markdown"}:
            return "resume_markdown"

        if source_extension in {".txt", ".text", ".html", ".htm"}:
            return "resume_text"

        if source_extension != ".json":
            raise ValueError(f"Unsupported import candidate format: '{source_extension or source_file_name}'.")

        return "json_document"

    def _detect_json_source_kind(self, document_payload: dict[str, object]) -> str:
        """Различает raw `portfolio.v1` и bundle JSON для корректного audit/source tracking."""

        snapshot_block = document_payload.get("snapshot")
        if isinstance(snapshot_block, dict):
            nested_payload = snapshot_block.get("payload")
            if isinstance(nested_payload, dict):
                return "import_bundle"

        version = document_payload.get("version")
        if version == "portfolio.v1":
            return "portfolio_json"

        raise ValueError("Provided JSON document is neither a portfolio bundle nor a raw portfolio.v1 payload.")
