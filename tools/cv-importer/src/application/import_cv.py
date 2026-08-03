"""Application-layer entrypoint для импорта резюме."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ImportCvCommand:
    """Команда импорта резюме в draft-формат."""

    source_path: Path
    target_directory: Path


def import_cv(command: ImportCvCommand) -> None:
    """Заглушка будущего сценария импорта.

    Реальная реализация должна:
    1. определить адаптер по типу файла;
    2. извлечь текст;
    3. распознать секции;
    4. сформировать draft и report;
    5. не публиковать данные автоматически.
    """

    _ = command
    raise NotImplementedError("CV importer will be implemented after Python runtime setup.")

