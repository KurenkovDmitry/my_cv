"""CLI конвертации исходного документа в `portfolio.v1`."""

from __future__ import annotations

import argparse
from pathlib import Path

from portfolio_cv_importer.application.commands import ConvertSourceToPortfolioCommand
from portfolio_cv_importer.application.service import CvImportExportService


def build_argument_parser() -> argparse.ArgumentParser:
    """Создаёт CLI parser конвертации входного документа."""

    argument_parser = argparse.ArgumentParser(
        prog="portfolio-cv-convert",
        description="Convert a resume-like source document into raw portfolio.v1 JSON.",
    )
    argument_parser.add_argument("source_path", type=Path)
    argument_parser.add_argument("target_path", type=Path)
    return argument_parser


def main() -> int:
    """Точка входа CLI конвертации."""

    parsed_arguments = build_argument_parser().parse_args()
    service = CvImportExportService()
    service.convert_source_to_portfolio(
        ConvertSourceToPortfolioCommand(
            source_path=parsed_arguments.source_path,
            target_path=parsed_arguments.target_path,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
