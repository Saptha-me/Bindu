# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""x402 Extension for Bindu Agents.

What is x402?
-------------
x402 is a protocol for agent-to-agent payments and economic interactions. It enables
autonomous agents to negotiate, request, and execute payments seamlessly without human
intervention. Think of it as the financial layer for the agent economy.

Unlike traditional payment systems that require human approval for every transaction,
x402 allows agents to autonomously manage budgets, negotiate prices, and complete
transactions based on predefined rules and mandates. This makes it perfect for
decentralized agent networks where economic coordination must happen at machine speed.

In Bindu, agents can use x402 to monetize their services, pay for resources, and
participate in the emerging agent economy. The protocol supports various payment
methods and provides strong guarantees through cryptographic mandates.

How It Works:
-------------
1. **Intent Mandates**: Users grant agents permission to spend within defined limits
2. **Cart Mandates**: Merchants create signed carts with items and prices
3. **Payment Negotiation**: Agents negotiate prices and payment terms autonomously
4. **Payment Execution**: Transactions are executed with cryptographic proof
5. **Settlement**: Payments are settled through various payment methods

This Module Provides:
---------------------
- Payment request and response handling
- Cart and intent mandate management
- Payment method negotiation
- Cryptographic mandate verification
- Integration with A2A protocol for seamless agent payments

Official Specification: https://www.x402.org

Inspired by the x402 protocol for enabling economic coordination between autonomous agents.
"""

from __future__ import annotations

__all__: list[str] = []
