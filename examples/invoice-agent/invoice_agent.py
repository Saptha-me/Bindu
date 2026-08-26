from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv
import os
import logging
import uuid
import json

load_dotenv()
logger = logging.getLogger(__name__)
# Simple in-memory storage

db = {}


def save_invoice(invoice):
    db[invoice["id"]] = invoice


def get_invoice_by_id(invoice_id):
    return db.get(invoice_id)


def list_invoices():
    return list(db.values())


# Core logic


def create_invoice(payload):
    if not isinstance(payload, dict) or "items" not in payload:
        raise ValueError("Invalid payload")

    if not isinstance(payload["items"], list) or not payload["items"]:
        raise ValueError("items must be a non-empty list")

    total = 0
    for i, item in enumerate(payload["items"]):
        qty = item.get("quantity")
        price = item.get("unit_price")

        if not isinstance(qty, (int, float)) or not isinstance(price, (int, float)):
            raise ValueError(f"Invalid item at index {i}")

        if qty <= 0 or price < 0:
            raise ValueError(f"Invalid values at index {i}")

        total += qty * price

    recipient_wallet = payload.get("recipient_wallet") or os.getenv(
        "AGENT_WALLET_ADDRESS"
    )

    if not recipient_wallet:
        raise ValueError("recipient_wallet is required")
    invoice = {
        "id": f"inv_{uuid.uuid4()}",
        "recipient": payload.get("recipient"),
        "recipient_wallet": recipient_wallet,
        "items": payload["items"],
        "currency": payload.get("currency", "USDC"),
        "total": total,
        "status": "pending",
    }

    save_invoice(invoice)
    return invoice


def verify_payment(invoice_id, tx_hash):
    invoice = get_invoice_by_id(invoice_id)

    if not invoice:
        return {"verified": False, "reason": "Invoice not found"}

    # mock verification
    invoice["status"] = "paid"
    invoice["tx_hash"] = tx_hash
    save_invoice(invoice)

    return {
        "verified": True,
        "settled_amount": invoice["total"],
        "reason": None,
    }


# Bindu config

config = {
    "author": "akash",
    "name": "invoice-agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "description": "Invoice agent with X402 payment flow",
    "version": "1.0.0",
    "capabilities": {
        "payments": ["invoice", "x402"],
    },
    "skills": ["skills/invoice-agent-skill"],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
}

# Handler (Bindu entry point)


def handler(messages):
    try:
        user_messages = [m for m in messages if m.get("role") == "user"]

        if not user_messages:
            return "No user message found"

        raw = user_messages[-1].get("parts", [{}])[0].get("text", "{}")

        try:
            input_data = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "bad_request", "message": "Invalid JSON input"}

        if input_data.get("type") == "generate_invoice":
            invoice = create_invoice(input_data.get("payload", {}))

            return {
                "invoice_id": invoice["id"],
                "total": invoice["total"],
                "payment_header": {
                    "amount": str(invoice["total"]),
                    "token": invoice.get("currency", "USDC"),
                    "network": os.getenv("X402_NETWORK", "base-sepolia"),
                    "pay_to_address": invoice["recipient_wallet"],
                },
            }

        if input_data.get("type") == "get_invoice":
            invoice = get_invoice_by_id(input_data.get("invoice_id"))

            if not invoice:
                return {
                    "error": "not_found",
                    "message": f"Invoice not found: {input_data.get('invoice_id')}",
                }

            return {"invoice": invoice}

        if input_data.get("type") == "list_invoices":
            return {"invoices": list_invoices()}

        if input_data.get("type") == "verify_payment":
            return verify_payment(
                input_data.get("invoice_id"),
                input_data.get("tx_hash"),
            )

        return "Unknown request type"

    except Exception:
        logger.exception("Unhandled error")
        return {"error": "internal_error", "message": "Internal Server Error"}


# Run agent

if __name__ == "__main__":
    print("Invoice Agent running...")
    bindufy(config, handler)
