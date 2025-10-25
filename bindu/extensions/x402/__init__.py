# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""x402 Extension for Bindu Agents - Following Google a2a-x402 Pattern.

What is x402?
-------------
x402 is a protocol for agent-to-agent payments and economic interactions. It enables
autonomous agents to negotiate, request, and execute payments seamlessly without human
intervention. Think of it as the financial layer for the agent economy.

This implementation follows the official Google a2a-x402 pattern:
https://github.com/google-agentic-commerce/a2a-x402

Architecture:
-------------
1. **Exception-Based Payment Requirements**: Agents throw exceptions to request payment
2. **Functional Core**: Pure functions for payment operations (verify, settle)
3. **Executor Middleware**: Automates the payment flow (verify→process→settle)
4. **State Management**: Uses A2A task metadata for payment state

How It Works:
-------------
1. Agent throws x402PaymentRequiredException when payment needed
2. Executor catches exception and returns payment-required response
3. Client submits payment
4. Executor verifies payment with facilitator
5. Agent processes request after verification
6. Executor settles payment on-chain after completion

Example Usage:
--------------
```python
from bindu.extensions.x402 import (
    x402PaymentRequiredException,
    require_payment,
    x402PaymentExecutor
)

# Option 1: Throw exception directly
if is_premium_feature(request):
    raise x402PaymentRequiredException.for_service(
        price="$5.00",
        pay_to_address="0x123...",
        resource="/premium-feature"
    )

# Option 2: Use decorator
@require_payment(price="$5.00", pay_to_address="0x123...", resource="/ai-service")
async def generate_content(task):
    return ai_service.generate(task)

# Option 3: Multiple tiers
raise x402PaymentRequiredException.for_tiered_service(
    tiers=[
        {"price": "$2.00", "description": "Basic"},
        {"price": "$5.00", "description": "Premium"},
    ],
    pay_to_address="0x123...",
    resource="/ai-service"
)
```

Official Specification: https://www.x402.org
"""

from __future__ import annotations

# New simplified API (a2a-x402 pattern)
from bindu.extensions.x402.exceptions import x402PaymentRequiredException
from bindu.extensions.x402.core import (
    # Core functions
    create_payment_requirements,
    verify_payment,
    settle_payment,
    # State management
    x402Utils,
    PaymentStatus,
    # Extension utilities
    get_extension_declaration,
    check_extension_activation,
    X402_EXTENSION_URI,
)
from bindu.extensions.x402.executor import (
    x402PaymentExecutor,
    require_payment,
)



__all__ = [
    # New simplified API
    "x402PaymentRequiredException",
    "x402PaymentExecutor",
    "require_payment",
    "create_payment_requirements",
    "verify_payment",
    "settle_payment",
    "x402Utils",
    "PaymentStatus",
    "get_extension_declaration",
    "check_extension_activation",
    "X402_EXTENSION_URI",
]
