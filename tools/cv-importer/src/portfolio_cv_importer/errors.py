"""Ошибки import/export контура."""

from __future__ import annotations


class CvImporterError(RuntimeError):
    """Базовая ошибка CV importer."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class UnsupportedSourceFormatError(CvImporterError):
    """Ошибка неподдерживаемого входного формата."""

    def __init__(self, source_file_name: str) -> None:
        super().__init__(
            "UNSUPPORTED_SOURCE_FORMAT",
            f"Unsupported source format for '{source_file_name}'.",
        )


class UnsupportedTargetFormatError(CvImporterError):
    """Ошибка неподдерживаемого выходного формата."""

    def __init__(self, target_file_name_or_format: str) -> None:
        super().__init__(
            "UNSUPPORTED_TARGET_FORMAT",
            f"Unsupported target format '{target_file_name_or_format}'.",
        )


class InvalidPortfolioDocumentError(CvImporterError):
    """Ошибка некорректного `portfolio.v1` или bundle-документа."""

    def __init__(self, message: str) -> None:
        super().__init__("INVALID_PORTFOLIO_DOCUMENT", message)
