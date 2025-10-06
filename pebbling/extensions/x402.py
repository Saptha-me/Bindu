"""Utilities for integrating the x402 payment extension with Septha servers."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from functools import cached_property
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from pebbling.common.protocol.types import AgentExtension
from x402.common import process_price_to_atomic_amount
from x402.encoding import safe_base64_decode
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    SettleResponse,
    VerifyResponse,
    x402PaymentRequiredResponse,
)


X_402_PAYMENT_HEADER = "X-402-Payment"
X_A2A_EXTENSIONS_HEADER = "X-A2A-Extensions"
X402_EXTENSION_URI = "https://saptha.dev/extensions/x402"
DEFAULT_FACILITATOR_URL = "https://x402.org/facilitator"


class X402Error(Exception):
    """Base exception for x402 integration errors."""


class PaymentVerificationError(X402Error):
    """Raised when a payment payload fails verification."""


class PaymentSettlementError(X402Error):
    """Raised when settlement fails after a successful verification."""


class AgentCostEntry(BaseModel):
    """Single priced work offering exposed via x402 extension."""

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=3, max_length=3)
    price: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)

    @field_validator("name", "description", "unit", mode="before")
    @classmethod
    def _strip_strings(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        if not value:
            raise ValueError("Value must be a non-empty string")
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Currency must be a string")
        value = value.strip().upper()
        if len(value) != 3:
            raise ValueError("Currency must be a 3-letter code")
        return value

    @field_validator("price", mode="before")
    @classmethod
    def _validate_price(cls, value: str) -> str:
        if isinstance(value, (int, float, Decimal)):
            decimal_value = Decimal(str(value))
            if decimal_value < 0:
                raise ValueError("Price must be non-negative")
            return format(decimal_value.normalize(), "f")
        elif isinstance(value, str):
            value = value.strip()
            try:
                decimal_value = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError("Price must be a numeric string") from exc
            if decimal_value < 0:
                raise ValueError("Price must be non-negative")
            return value
        else:
            raise ValueError("Price must be a numeric value")


class AgentCostCard(BaseModel):
    """Collection of cost entries attached to x402 extension."""

    version: str = "1.0"
    entries: list[AgentCostEntry]
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _ensure_entries(self) -> "AgentCostCard":
        if not self.entries:
            raise ValueError("cost card entries must not be empty")
        return self


@dataclass
class x402ExtensionConfig:
    """Configuration for the Septha x402 extension declaration."""

    extension_uri: str = X402_EXTENSION_URI
    version: str = "0.1"
    x402_version: int = 1
    required: bool = True
    description: str = "Supports x402 payments"


@dataclass
class x402ServerConfig:
    """Payment requirement configuration used to build challenges."""

    price: Any
    pay_to_address: str
    network: str = "base"
    description: str = "Payment required"
    mime_type: str = "application/json"
    max_timeout_seconds: int = 600
    resource: Optional[str] = None
    asset_address: Optional[str] = None


@dataclass
class PaymentSettlement:
    """Successful payment verification and settlement."""

    payment_payload: PaymentPayload
    verify_response: VerifyResponse
    settle_response: SettleResponse
    settlement_header: str


@dataclass
class PaymentEvaluationResult:
    """Result of evaluating a request for x402 compliance."""

    challenge_payload: Optional[dict[str, Any]] = None
    settlement: Optional[PaymentSettlement] = None

    @property
    def requires_challenge(self) -> bool:
        return self.challenge_payload is not None

    @property
    def has_settlement(self) -> bool:
        return self.settlement is not None


@dataclass
class X402PaymentManager:
    """Builds payment requirements and verifies x402 settlements."""

    extension_config: x402ExtensionConfig
    server_config: x402ServerConfig
    facilitator_url: str = DEFAULT_FACILITATOR_URL
    required: bool = True
    enabled: bool = False
    http_timeout: float = 10.0
    cost_card: Optional[AgentCostCard] = None

    def __post_init__(self) -> None:
        if self.cost_card and not isinstance(self.cost_card, AgentCostCard):
            self.cost_card = AgentCostCard.model_validate(self.cost_card)

    def evaluate_request(self, headers: Mapping[str, str]) -> PaymentEvaluationResult:
        """Evaluate incoming request headers and determine next step."""

        if not self.enabled:
            return PaymentEvaluationResult()

        extension_header = headers.get(X_A2A_EXTENSIONS_HEADER, "")
        wants_extension = X402_EXTENSION_URI in extension_header
        payment_header = headers.get(X_402_PAYMENT_HEADER)

        if not payment_header:
            if self.required or wants_extension:
                return PaymentEvaluationResult(challenge_payload=self._build_payment_required_payload())
            return PaymentEvaluationResult()

        settlement = self.verify_and_settle(payment_header)
        return PaymentEvaluationResult(settlement=settlement)

    @cached_property
    def agent_extension(self) -> AgentExtension:
        """Expose AgentExtension metadata for manifests."""

        params: dict[str, Any] = {
            "network": self.server_config.network,
            "pay_to": self.server_config.pay_to_address,
            "max_timeout_seconds": self.server_config.max_timeout_seconds,
        }
        if self.server_config.asset_address:
            params["asset"] = self.server_config.asset_address
        if self.cost_card:
            params["cost_card"] = self.cost_card.model_dump(exclude_none=True)

        return AgentExtension(
            uri=self.extension_config.extension_uri,
            description=self.extension_config.description,
            required=self.extension_config.required,
            params=params,
        )

    @cached_property
    def payment_requirements(self) -> PaymentRequirements:
        """Cached payment requirements derived from server configuration."""

        price = self.server_config.price
        price_input: Any
        if isinstance(price, (int, float)):
            price_input = price
        elif hasattr(price, "amount"):
            price_input = getattr(price, "amount")
        else:
            price_input = str(price)

        max_amount_required, default_asset, extra = process_price_to_atomic_amount(price_input, self.server_config.network)

        asset = self.server_config.asset_address or default_asset

        return PaymentRequirements(
            scheme="exact",
            network=self.server_config.network,
            max_amount_required=max_amount_required,
            pay_to=self.server_config.pay_to_address,
            resource=self.server_config.resource or "",
            description=self.server_config.description,
            mime_type=self.server_config.mime_type,
            max_timeout_seconds=self.server_config.max_timeout_seconds,
            asset=asset,
            extra=extra,
        )

    def verify_and_settle(self, payment_header: str) -> PaymentSettlement:
        """Verify payment payload and settle via facilitator."""

        payload_obj = self._decode_payment_payload(payment_header)
        request_payload = {
            "x402Version": self.extension_config.x402_version,
            "paymentPayload": payload_obj.model_dump(by_alias=True),
            "paymentRequirements": self.payment_requirements.model_dump(by_alias=True, exclude_none=True),
        }

        verify_data = self._post_to_facilitator("verify", request_payload)
        verify_response = VerifyResponse(**verify_data)
        if not verify_response.is_valid:
            raise PaymentVerificationError("x402 verification failed")

        settle_data = self._post_to_facilitator("settle", request_payload)
        settle_response = SettleResponse(**settle_data)
        if not settle_response.success:
            raise PaymentSettlementError("x402 settlement failed")

        settlement_header = base64.b64encode(settle_response.model_dump_json().encode("utf-8")).decode("utf-8")

        return PaymentSettlement(
            payment_payload=payload_obj,
            verify_response=verify_response,
            settle_response=settle_response,
            settlement_header=settlement_header,
        )

    def _decode_payment_payload(self, payment_header: str) -> PaymentPayload:
        try:
            decoded = safe_base64_decode(payment_header)
            payload_dict = json.loads(decoded)
        except Exception as exc:  # pragma: no cover - defensive path
            raise PaymentVerificationError("Invalid x402 payment header") from exc

        return PaymentPayload(**payload_dict)

    def _build_payment_required_payload(self) -> dict[str, Any]:
        response = x402PaymentRequiredResponse(
            x402_version=self.extension_config.x402_version,
            accepts=[self.payment_requirements],
            error="",
        )
        return response.model_dump(by_alias=True, exclude_none=True)

    def _post_to_facilitator(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.facilitator_url.rstrip('/')}/{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urlopen(request, timeout=self.http_timeout) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.fp else exc.reason
            raise PaymentSettlementError(f"Facilitator returned HTTP {exc.code}: {error_body}") from exc
        except URLError as exc:  # pragma: no cover - network errors
            raise PaymentSettlementError(f"Unable to reach facilitator: {exc.reason}") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive path
            raise PaymentSettlementError("Invalid JSON from facilitator") from exc


def build_cost_card(entries: Sequence[Mapping[str, Any]], notes: Optional[str] = None) -> AgentCostCard:
    """Construct an AgentCostCard from raw configuration values."""

    try:
        cost_entries = [AgentCostEntry.model_validate(entry) for entry in entries]
        return AgentCostCard(entries=cost_entries, notes=notes)
    except ValidationError as exc:  # pragma: no cover - validation error surface
        raise ValueError(f"Invalid x402 cost card configuration: {exc}") from exc


def build_payment_manager(config: Mapping[str, Any] | Any) -> X402PaymentManager:
    """Create an x402 payment manager from a mapping or config object."""

    def _get(key: str, default: Any = None, required: bool = False) -> Any:
        if isinstance(config, Mapping):
            value = config.get(key, default)
        else:
            value = getattr(config, key, default)
        if required and value is None:
            raise ValueError(f"x402 configuration missing required field '{key}'")
        return value

    extension = x402ExtensionConfig(
        extension_uri=_get("extension_uri", X402_EXTENSION_URI) or X402_EXTENSION_URI,
        version=_get("version", "0.1"),
        x402_version=_get("x402_version", 1),
        required=_get("required", True),
        description=_get("extension_description", "Supports x402 payments") or "Supports x402 payments",
    )

    server = x402ServerConfig(
        price=_get("price", required=True),
        pay_to_address=_get("pay_to_address", required=True),
        network=_get("network", "base"),
        description=_get("description", "Payment required"),
        mime_type=_get("mime_type", "application/json"),
        max_timeout_seconds=_get("max_timeout_seconds", 600),
        resource=_get("resource", None),
        asset_address=_get("asset_address", None),
    )

    cost_entries = _get("cost_entries")
    cost_card = None
    if cost_entries:
        cost_card = build_cost_card(cost_entries, _get("cost_notes"))

    return X402PaymentManager(
        extension_config=extension,
        server_config=server,
        facilitator_url=_get("facilitator_url", DEFAULT_FACILITATOR_URL),
        required=_get("required", True),
        enabled=_get("enabled", True),
        http_timeout=_get("timeout_seconds", 10.0),
        cost_card=cost_card,
    )


def ensure_extension_header(existing_header: str | None, uri: str) -> str:
    """Merge extension URIs for the response header."""

    values = []
    if existing_header:
        values = [item.strip() for item in existing_header.split(",") if item.strip()]

    if uri not in values:
        values.append(uri)

    return ", ".join(values)
