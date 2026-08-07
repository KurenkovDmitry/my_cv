"""Полевой diff и безопасное применение выбранных изменений import candidate."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_MISSING = object()
_SYSTEM_ROOT_FIELDS = {"version", "draft", "needsManualReview"}
_STABLE_ITEM_PREFIX = "@id="


def build_import_field_review(
    current_payload: dict[str, object],
    candidate_payload: dict[str, object],
) -> list[dict[str, Any]]:
    """Строит Git-подобный список различий по отдельным полям документа."""

    review_fields: list[dict[str, Any]] = []
    _collect_changes(current_payload, candidate_payload, [], review_fields)
    return review_fields


def apply_import_field_patches(
    current_payload: dict[str, object],
    candidate_payload: dict[str, object],
    requested_patches: list[dict[str, Any]],
) -> tuple[dict[str, object], list[str]]:
    """Применяет проверенный набор полевых изменений к копии текущего draft."""

    available_changes = {
        str(review_field["path"]): str(review_field["operation"])
        for review_field in build_import_field_review(current_payload, candidate_payload)
    }
    if not requested_patches:
        raise ValueError("Field replace requires at least one selected field.")

    normalized_patches: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for requested_patch in requested_patches:
        path = requested_patch.get("path")
        operation = requested_patch.get("operation")
        if not isinstance(path, str) or not path.startswith("/") or len(path) > 512:
            raise ValueError("Every field patch must contain a valid JSON pointer path.")
        if path in seen_paths:
            raise ValueError(f"Field patch path '{path}' is duplicated.")
        if operation not in {"set", "remove"}:
            raise ValueError(f"Field patch '{path}' has an unsupported operation.")
        if available_changes.get(path) != operation:
            raise ValueError(f"Field patch '{path}' is not present in the candidate review.")

        normalized_patches.append(requested_patch)
        seen_paths.add(path)

    next_payload = deepcopy(current_payload)
    for normalized_patch in normalized_patches:
        path = str(normalized_patch["path"])
        operation = str(normalized_patch["operation"])
        path_segments = _decode_pointer(path)
        if not path_segments or path_segments[0] in _SYSTEM_ROOT_FIELDS:
            raise ValueError(f"Field patch '{path}' targets a protected root field.")

        if operation == "remove":
            _remove_path(next_payload, path_segments)
        else:
            _set_path(next_payload, path_segments, deepcopy(normalized_patch.get("value")))

    return next_payload, [str(patch["path"]) for patch in normalized_patches]


def _collect_changes(
    current_value: Any,
    candidate_value: Any,
    path_segments: list[str],
    target: list[dict[str, Any]],
) -> None:
    if current_value is not _MISSING and candidate_value is not _MISSING and current_value == candidate_value:
        return

    if isinstance(current_value, dict) and isinstance(candidate_value, dict):
        all_keys = sorted(set(current_value) | set(candidate_value))
        for key in all_keys:
            if not path_segments and key in _SYSTEM_ROOT_FIELDS:
                continue
            _collect_changes(
                current_value.get(key, _MISSING),
                candidate_value.get(key, _MISSING),
                [*path_segments, key],
                target,
            )
        return

    if isinstance(current_value, list) and isinstance(candidate_value, list):
        current_by_id = _index_stable_items(current_value)
        candidate_by_id = _index_stable_items(candidate_value)
        if current_by_id is not None and candidate_by_id is not None and (current_by_id or candidate_by_id):
            stable_ids = list(candidate_by_id)
            stable_ids.extend(item_id for item_id in current_by_id if item_id not in candidate_by_id)
            for item_id in stable_ids:
                _collect_changes(
                    current_by_id.get(item_id, _MISSING),
                    candidate_by_id.get(item_id, _MISSING),
                    [*path_segments, f"{_STABLE_ITEM_PREFIX}{item_id}"],
                    target,
                )
            return

    path = _encode_pointer(path_segments)
    operation = "remove" if candidate_value is _MISSING else "set"
    target.append(
        {
            "path": path,
            "section": path_segments[0] if path_segments else "root",
            "label": _build_field_label(path_segments),
            "operation": operation,
            "changeKind": _resolve_change_kind(current_value, candidate_value),
            "hasCurrentValue": current_value is not _MISSING,
            "hasCandidateValue": candidate_value is not _MISSING,
            "currentValue": None if current_value is _MISSING else deepcopy(current_value),
            "candidateValue": None if candidate_value is _MISSING else deepcopy(candidate_value),
        },
    )


def _index_stable_items(values: list[Any]) -> dict[str, dict[str, Any]] | None:
    if not values:
        return {}

    indexed_items: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            return None
        item_id = value.get("id")
        if not isinstance(item_id, str) or not item_id or item_id in indexed_items:
            return None
        indexed_items[item_id] = value
    return indexed_items


def _resolve_change_kind(current_value: Any, candidate_value: Any) -> str:
    if current_value is _MISSING:
        return "added"
    if candidate_value is _MISSING:
        return "removed"
    return "changed"


def _build_field_label(path_segments: list[str]) -> str:
    readable_segments = [
        segment.removeprefix(_STABLE_ITEM_PREFIX) if segment.startswith(_STABLE_ITEM_PREFIX) else segment
        for segment in path_segments
    ]
    return " / ".join(readable_segments)


def _encode_pointer(path_segments: list[str]) -> str:
    return "/" + "/".join(segment.replace("~", "~0").replace("/", "~1") for segment in path_segments)


def _decode_pointer(path: str) -> list[str]:
    return [segment.replace("~1", "/").replace("~0", "~") for segment in path.removeprefix("/").split("/")]


def _set_path(root: dict[str, object], path_segments: list[str], value: Any) -> None:
    parent, final_segment = _resolve_parent(root, path_segments, create_missing=True)
    if isinstance(parent, dict):
        parent[final_segment] = value
        return

    if isinstance(parent, list):
        item_index = _find_list_item_index(parent, final_segment)
        if item_index is None:
            if final_segment.startswith(_STABLE_ITEM_PREFIX):
                parent.append(value)
                return
            raise ValueError(f"List target '{final_segment}' does not exist.")
        parent[item_index] = value
        return

    raise ValueError("Field patch parent is not a container.")


def _remove_path(root: dict[str, object], path_segments: list[str]) -> None:
    parent, final_segment = _resolve_parent(root, path_segments, create_missing=False)
    if isinstance(parent, dict):
        parent.pop(final_segment, None)
        return
    if isinstance(parent, list):
        item_index = _find_list_item_index(parent, final_segment)
        if item_index is not None:
            parent.pop(item_index)


def _resolve_parent(root: dict[str, object], path_segments: list[str], *, create_missing: bool) -> tuple[Any, str]:
    if len(path_segments) == 1:
        return root, path_segments[0]

    current: Any = root
    for segment_index, segment in enumerate(path_segments[:-1]):
        next_segment = path_segments[segment_index + 1]
        if isinstance(current, dict):
            if segment not in current:
                if not create_missing:
                    return {}, path_segments[-1]
                current[segment] = [] if next_segment.startswith(_STABLE_ITEM_PREFIX) else {}
            current = current[segment]
            continue

        if isinstance(current, list):
            item_index = _find_list_item_index(current, segment)
            if item_index is None:
                if not create_missing or not segment.startswith(_STABLE_ITEM_PREFIX):
                    raise ValueError(f"List target '{segment}' does not exist.")
                new_item: dict[str, Any] = {"id": segment.removeprefix(_STABLE_ITEM_PREFIX)}
                current.append(new_item)
                current = new_item
            else:
                current = current[item_index]
            continue

        raise ValueError(f"Path segment '{segment}' does not point to a container.")

    return current, path_segments[-1]


def _find_list_item_index(values: list[Any], selector: str) -> int | None:
    if selector.startswith(_STABLE_ITEM_PREFIX):
        target_id = selector.removeprefix(_STABLE_ITEM_PREFIX)
        return next(
            (
                item_index
                for item_index, item in enumerate(values)
                if isinstance(item, dict) and item.get("id") == target_id
            ),
            None,
        )

    if selector.isdigit():
        numeric_index = int(selector)
        return numeric_index if numeric_index < len(values) else None
    return None
