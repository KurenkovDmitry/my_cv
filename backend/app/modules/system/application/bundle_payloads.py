"""Вспомогательные функции для чтения portfolio payload из bundle и raw JSON."""

from __future__ import annotations

from typing import Any


def extract_portfolio_payload(document_payload: dict[str, Any]) -> dict[str, Any]:
    """Извлекает `portfolio.v1` payload из raw документа или export/import bundle."""

    snapshot_block = document_payload.get("snapshot")
    if isinstance(snapshot_block, dict):
        nested_payload = snapshot_block.get("payload")
        if isinstance(nested_payload, dict):
            return dict(nested_payload)

    version = document_payload.get("version")
    if version == "portfolio.v1":
        return dict(document_payload)

    raise ValueError("Provided JSON document is neither a portfolio bundle nor a raw portfolio.v1 payload.")
