"""Мост к native C++ PDF extractor без OCR."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from portfolio_cv_importer.extractors.pdf_text_extractor import extract_lines_from_pdf_bytes

NATIVE_PDF_BINARY_ENV = "PORTFOLIO_RESUME_NATIVE_PDF_BINARY"


def extract_lines_from_pdf_with_optional_native_bridge(pdf_bytes: bytes) -> list[str]:
    """Пытается использовать native extractor, а при недоступности уходит в pure Python fallback."""

    native_binary = os.environ.get(NATIVE_PDF_BINARY_ENV, "").strip()
    if not native_binary:
        return extract_lines_from_pdf_bytes(pdf_bytes)

    resolved_binary = Path(native_binary)
    if not resolved_binary.exists():
        return extract_lines_from_pdf_bytes(pdf_bytes)

    return extract_lines_with_native_binary(pdf_bytes, resolved_binary)


def extract_lines_with_native_binary(pdf_bytes: bytes, native_binary_path: Path) -> list[str]:
    """Извлекает строки через внешний C++ CLI, чтобы Python не держал низкоуровневый parser в runtime-петле."""

    with tempfile.TemporaryDirectory(prefix="portfolio-cv-importer-") as temporary_directory:
        source_path = Path(temporary_directory) / "source.pdf"
        source_path.write_bytes(pdf_bytes)

        completed_process = subprocess.run(
            [str(native_binary_path), str(source_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    return [line.strip() for line in completed_process.stdout.splitlines() if line.strip()]
