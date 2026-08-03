"""Контрактные тесты Python API для content-diff-native."""

from content_diff_native import compare_documents


def test_compare_documents_reports_changed_top_level_sections() -> None:
    """Проверяет, что diff summary возвращает изменённые верхнеуровневые разделы."""

    left_payload = {
        "profile": {"displayName": {"ru": "A", "en": "A"}},
        "projects": [{"slug": "one"}],
    }
    right_payload = {
        "profile": {"displayName": {"ru": "B", "en": "B"}},
        "projects": [{"slug": "one"}],
        "legal": {"analyticsConsent": {"version": "2026-08-03"}},
    }

    diff_summary = compare_documents(left_payload, right_payload)

    assert diff_summary["summary"]["changedPathsCount"] >= 2
    assert "profile" in diff_summary["sections"]
    assert "legal" in diff_summary["sections"]
