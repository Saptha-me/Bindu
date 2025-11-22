# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Bindu Agent Extensions.

Extensions are modular capabilities that agents can optionally support to enhance their
functionality. Following the A2A Protocol specification, extensions provide a standardized
way to add features without modifying the core protocol.

Why Extensions?
---------------
In a decentralized agent network, not every agent needs every capability. Extensions allow:
- **Modularity**: Agents choose which features to support
- **Discoverability**: Clients can detect capabilities through agent cards
- **Interoperability**: Standard extension format ensures compatibility
- **Flexibility**: New capabilities can be added without breaking existing agents

Available Extensions:
---------------------

**DID (Decentralized Identifier)**
Provides cryptographic identity management using Ed25519 keys and W3C-compliant DID
documents. Every agent gets a unique, self-sovereign identity that can be verified
without relying on centralized authorities.

**x402 (Agent Payments Protocol)**
Enables autonomous agent-to-agent payments and economic interactions. Agents can
negotiate prices, request payments, and execute transactions based on cryptographic
mandates, creating a true agent economy.


Each extension follows the A2A protocol specification for extensions:
https://a2a-protocol.org/v0.3.0/topics/extensions/

This modular approach enables the Bindu ecosystem to evolve and grow while maintaining
backward compatibility and interoperability across the agent swarm.
"""

from __future__ import annotations

__all__: list[str] = []
