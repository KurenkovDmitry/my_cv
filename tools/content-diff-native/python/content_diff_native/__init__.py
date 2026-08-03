"""Python API для native diff engine."""

from __future__ import annotations

import json
from typing import Any

try:
    from ._native import compare_documents_json as _compare_documents_json
except ImportError:  # pragma: no cover - fallback нужен на этапе scaffold и локальной разработки.
    _compare_documents_json = None


def _fallback_compare(left_payload: dict[str, Any], right_payload: dict[str, Any]) -> dict[str, Any]:
    """Простой Python fallback, пока native extension не собрана."""

    changed_paths: list[str] = []
    changed_sections: set[str] = set()

    left_keys = set(left_payload.keys())
    right_keys = set(right_payload.keys())

    for top_level_key in sorted(left_keys | right_keys):
        if left_payload.get(top_level_key) != right_payload.get(top_level_key):
            changed_paths.append(top_level_key)
            changed_sections.add(top_level_key.split(".")[0])

    return {
        "summary": {
            "changedPathsCount": len(changed_paths),
            "sectionsChangedCount": len(changed_sections),
        },
        "changedPaths": changed_paths,
        "sections": sorted(changed_sections),
    }


def compare_documents(left_payload: dict[str, Any], right_payload: dict[str, Any]) -> dict[str, Any]:
    """Сравнивает два документа и возвращает JSON-friendly diff summary."""

    if _compare_documents_json is None:
        return _fallback_compare(left_payload, right_payload)

    left_json = json.dumps(left_payload, ensure_ascii=False, sort_keys=True, indent=2)
    right_json = json.dumps(right_payload, ensure_ascii=False, sort_keys=True, indent=2)
    return json.loads(_compare_documents_json(left_json, right_json))


__all__ = ["compare_documents"]
