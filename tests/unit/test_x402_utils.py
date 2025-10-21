"""Unit tests for x402 metadata utilities."""

import pytest

from bindu.extensions.x402.utils import (
    build_payment_completed_metadata,
    build_payment_failed_metadata,
    build_payment_required_metadata,
    build_payment_verified_metadata,
)
from bindu.settings import app_settings

pytestmark = pytest.mark.x402


class TestX402Utils:
    def test_build_payment_required_metadata(self):
        req = {"accepts": [{"scheme": "exact"}]}
        md = build_payment_required_metadata(req)
        assert (
            md[app_settings.x402.meta_status_key] == app_settings.x402.status_required
        )
        assert md[app_settings.x402.meta_required_key] is req

    def test_build_payment_verified_metadata(self):
        md = build_payment_verified_metadata()
        assert (
            md[app_settings.x402.meta_status_key] == app_settings.x402.status_verified
        )

    def test_build_payment_completed_metadata(self):
        receipt = {"tx": "0xabc"}
        md = build_payment_completed_metadata(receipt)
        assert (
            md[app_settings.x402.meta_status_key] == app_settings.x402.status_completed
        )
        assert md[app_settings.x402.meta_receipts_key] == [receipt]

    def test_build_payment_failed_metadata(self):
        md = build_payment_failed_metadata("verification_failed")
        assert md[app_settings.x402.meta_status_key] == app_settings.x402.status_failed
        assert md[app_settings.x402.meta_error_key] == "verification_failed"
