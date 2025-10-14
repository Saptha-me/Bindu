"""Small helpers for recording x402 payment metadata on Tasks.

These utilities keep metadata writes consistent and centralized.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..x402.constants import X402Metadata


def merge_task_metadata(task: dict, updates: Dict[str, Any]) -> dict:
    """Merge metadata updates into a task dict in-place and return it."""
    if "metadata" not in task or task["metadata"] is None:
        task["metadata"] = {}
    task["metadata"].update(updates)
    return task


def build_payment_required_metadata(required: dict) -> dict:
    return {
        X402Metadata.STATUS_KEY: "payment-required",
        X402Metadata.REQUIRED_KEY: required,
    }


def build_payment_verified_metadata() -> dict:
    return {X402Metadata.STATUS_KEY: "payment-verified"}


def build_payment_completed_metadata(receipt: dict) -> dict:
    return {
        X402Metadata.STATUS_KEY: "payment-completed",
        X402Metadata.RECEIPTS_KEY: [receipt],
    }


def build_payment_failed_metadata(error: str, receipt: Optional[dict] = None) -> dict:
    md = {X402Metadata.STATUS_KEY: "payment-failed", X402Metadata.ERROR_KEY: error}
    if receipt:
        md[X402Metadata.RECEIPTS_KEY] = [receipt]
    return md
