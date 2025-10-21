"""Small helpers for recording x402 payment metadata on Tasks.

These utilities keep metadata writes consistent and centralized.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from bindu.settings import app_settings


def merge_task_metadata(task: dict, updates: Dict[str, Any]) -> dict:
    """Merge metadata updates into a task dict in-place and return it."""
    if "metadata" not in task or task["metadata"] is None:
        task["metadata"] = {}
    task["metadata"].update(updates)
    return task


def build_payment_required_metadata(required: dict) -> dict:
    """Build metadata dict for payment-required state."""
    return {
        app_settings.x402.meta_status_key: app_settings.x402.status_required,
        app_settings.x402.meta_required_key: required,
    }


def build_payment_verified_metadata() -> dict:
    """Build metadata dict for payment-verified state."""
    return {app_settings.x402.meta_status_key: app_settings.x402.status_verified}


def build_payment_completed_metadata(receipt: dict) -> dict:
    """Build metadata dict for payment-completed state."""
    return {
        app_settings.x402.meta_status_key: app_settings.x402.status_completed,
        app_settings.x402.meta_receipts_key: [receipt],
    }


def build_payment_failed_metadata(error: str, receipt: Optional[dict] = None) -> dict:
    """Build metadata dict for payment-failed state."""
    md = {
        app_settings.x402.meta_status_key: app_settings.x402.status_failed,
        app_settings.x402.meta_error_key: error,
    }
    if receipt:
        md[app_settings.x402.meta_receipts_key] = [receipt]
    return md
