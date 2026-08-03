"""Adapter native/Python compare engine для backup и import candidate diff."""

from __future__ import annotations

import asyncio
import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, cast

from app.modules.system.domain.diff_engine import ContentDiffEngine, ContentDiffRecord


def _load_compare_documents_callable() -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    """Подключает Python API native diff engine из локального tools-каталога."""

    tools_python_path = Path(__file__).resolve().parents[5] / "tools" / "content-diff-native" / "python"
    if str(tools_python_path) not in sys.path:
        sys.path.insert(0, str(tools_python_path))

    content_diff_module = import_module("content_diff_native")
    compare_documents = getattr(content_diff_module, "compare_documents")
    return cast(Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]], compare_documents)


class NativeContentDiffEngine(ContentDiffEngine):
    """Использует Python API native diff engine с безопасным fallback внутри пакета."""

    def __init__(self) -> None:
        self._compare_documents = _load_compare_documents_callable()

    async def compare(
        self,
        *,
        left_payload: dict[str, object],
        right_payload: dict[str, object],
        left_label: str,
        right_label: str,
    ) -> ContentDiffRecord:
        """Сравнивает два документа и возвращает компактный summary diff."""

        raw_diff = await asyncio.to_thread(
            self._compare_documents,
            dict(left_payload),
            dict(right_payload),
        )
        summary_block = raw_diff.get("summary") if isinstance(raw_diff, dict) else None

        return ContentDiffRecord(
            left_label=left_label,
            right_label=right_label,
            changed_paths=_pick_string_list(raw_diff.get("changedPaths")) if isinstance(raw_diff, dict) else [],
            sections=_pick_string_list(raw_diff.get("sections")) if isinstance(raw_diff, dict) else [],
            changed_paths_count=_pick_int(summary_block, "changedPathsCount"),
            sections_changed_count=_pick_int(summary_block, "sectionsChangedCount"),
        )


def _pick_string_list(value: object) -> list[str]:
    """Возвращает только строковые значения из потенциально произвольного списка."""

    if not isinstance(value, list):
        return []

    return [entry for entry in value if isinstance(entry, str)]


def _pick_int(summary_block: object, key: str) -> int:
    """Безопасно извлекает целое число из summary-блока diff."""

    if not isinstance(summary_block, dict):
        return 0

    raw_value = summary_block.get(key)
    return raw_value if isinstance(raw_value, int) else 0
