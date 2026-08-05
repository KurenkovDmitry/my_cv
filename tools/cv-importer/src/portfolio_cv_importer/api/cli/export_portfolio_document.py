"""CLI экспорта `portfolio.v1` в bundle или resume-like документ."""

from __future__ import annotations

import argparse
from pathlib import Path

from portfolio_cv_importer.application.commands import ExportPortfolioDocumentCommand
from portfolio_cv_importer.application.service import CvImportExportService


def build_argument_parser() -> argparse.ArgumentParser:
    """Создаёт CLI parser экспорта портфолио."""

    argument_parser = argparse.ArgumentParser(
        prog="portfolio-cv-export",
        description="Export raw portfolio.v1 JSON into bundle or resume-like markdown.",
    )
    argument_parser.add_argument("source_path", type=Path)
    argument_parser.add_argument("target_path", type=Path)
    argument_parser.add_argument("--target-format", dest="target_format", type=str, default=None)
    return argument_parser


def main() -> int:
    """Точка входа CLI экспорта."""

    parsed_arguments = build_argument_parser().parse_args()
    service = CvImportExportService()
    service.export_portfolio_document(
        ExportPortfolioDocumentCommand(
            source_path=parsed_arguments.source_path,
            target_path=parsed_arguments.target_path,
            target_format=parsed_arguments.target_format,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
