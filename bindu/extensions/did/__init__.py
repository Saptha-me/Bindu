# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DID (Decentralized Identifier) Extension for Bindu Agents.

What is a DID?
--------------
A DID is a globally unique identifier that doesn't require a central authority to issue it.
Think of it as a self-sovereign identity - you create it, you own it, you control it.

Unlike traditional identifiers (emails, usernames) that depend on centralized services,
DIDs are cryptographically verifiable and can be resolved to discover public keys and
service endpoints. This makes them perfect for decentralized agent networks where trust
must be established without intermediaries.

In Bindu, every agent has a DID that serves as its permanent, portable identity across
the entire swarm. The DID format we use is: `did:bindu:{author}:{agent_name}`

How It Works:
-------------
1. **Key Generation**: Each agent generates an Ed25519 key pair
2. **DID Creation**: The public key is used to derive a unique DID
3. **DID Document**: A W3C-compliant document containing public keys and endpoints
4. **Resolution**: Other agents can resolve a DID to verify identity and find services
5. **Signatures**: Agents sign messages with their private key for authentication

This Module Provides:
---------------------
- Key generation and management (Ed25519)
- DID creation and resolution
- Digital signatures and verification
- W3C-compliant DID documents
- Validation utilities

Inspired by AT Protocol's DID implementation: https://atproto.com/specs/did
"""

from __future__ import annotations

from bindu.extensions.did.did_agent_extension import DIDAgentExtension
from bindu.extensions.did.validation import DIDValidation

__all__ = [
    "DIDAgentExtension",
    "DIDValidation",
]
