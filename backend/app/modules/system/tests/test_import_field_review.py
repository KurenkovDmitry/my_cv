"""Тесты полевого review и применения выбранных изменений."""

from __future__ import annotations

from app.modules.system.application.import_field_review import (
    apply_import_field_patches,
    build_import_field_review,
)


def test_field_review_uses_stable_ids_in_lists() -> None:
    current = {
        "version": "portfolio.v1",
        "projects": [{"id": "alpha", "title": {"ru": "Старое", "en": "Old"}}],
    }
    candidate = {
        "version": "portfolio.v1",
        "projects": [{"id": "alpha", "title": {"ru": "Новое", "en": "New"}}],
    }

    review = build_import_field_review(current, candidate)

    assert {item["path"] for item in review} == {
        "/projects/@id=alpha/title/en",
        "/projects/@id=alpha/title/ru",
    }


def test_field_patch_can_edit_selected_value_and_keep_unselected_value() -> None:
    current = {
        "version": "portfolio.v1",
        "profile": {"displayName": {"ru": "Старое имя", "en": "Old name"}},
    }
    candidate = {
        "version": "portfolio.v1",
        "profile": {"displayName": {"ru": "Имя из CV", "en": "CV name"}},
    }

    next_payload, applied_paths = apply_import_field_patches(
        current,
        candidate,
        [{"path": "/profile/displayName/ru", "operation": "set", "value": "Исправленное имя"}],
    )

    assert applied_paths == ["/profile/displayName/ru"]
    assert next_payload["profile"]["displayName"] == {"ru": "Исправленное имя", "en": "Old name"}
