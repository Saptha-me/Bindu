# 🤝 Escrow Arbiter Agent

![Bindu X402 Compatible](https://img.shields.io/badge/Payments-X402_Native-blue)
![Network](https://img.shields.io/badge/Network-Base_Sepolia-purple)

A native Bindu agent that acts as a secure, automated middleman for cross-agent transactions. 

## The "Why"
Bindu is building the identity, communication, and payments layer for the Internet of Agents. For agents to truly collaborate and exchange value securely, they need trustless escrow systems. 

Instead of fighting the framework with custom web3 wrappers, this agent natively leverages Bindu's **X402 Payment Protocol** and decentralized identifiers (DIDs). It proves that agents shouldn't just respond—they should conditionally hold, verify, and route real economic value.

## How It Works
The Escrow Arbiter gates its core verification logic behind Bindu's paywall infrastructure. 

1. **Initiation:** The agent requires a $5.00 USDC payment on the Base Sepolia testnet to execute its primary method.
2. **Verification:** Once the Bindu network verifies the on-chain payment session, the agent's protected `escrow_handler` is triggered.
3. **Settlement:** The agent evaluates the proof of work provided in the message context. If the conditions are met, the transaction is settled.

## Setup & Testing
To run this agent locally:
1. Sync the environment (`uv sync`).
2. Run the agent: `python .agents/escrow_agent/agent.py`
3. Initiate a payment session using the Bindu X402 `/api/start-payment-session` endpoint.