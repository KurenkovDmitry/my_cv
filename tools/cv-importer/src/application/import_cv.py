"""Совместимый entrypoint старого import_cv сценария."""

from pathlib import Path

from portfolio_cv_importer.application.commands import ConvertSourceToPortfolioCommand
from portfolio_cv_importer.application.service import CvImportExportService


class ImportCvCommand:
    """Команда импорта резюме в raw `portfolio.v1`."""

    def __init__(self, source_path: Path, target_directory: Path) -> None:
        self.source_path = source_path
        self.target_directory = target_directory


def import_cv(command: ImportCvCommand) -> None:
    """Совместимый фасад поверх нового Python import/export пайплайна."""

    target_path = command.target_directory / f"{command.source_path.stem}.portfolio.v1.json"
    CvImportExportService().convert_source_to_portfolio(
        ConvertSourceToPortfolioCommand(
            source_path=command.source_path,
            target_path=target_path,
        ),
    )
