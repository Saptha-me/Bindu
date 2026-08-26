# Mortgage Comparison Agent

A powerful, multi-agent system built with **CrewAI** and **Bindu** that orchestrates complex financial reasoning while ensuring compliance.

## 🤖 What It Is
This is a **Composite Agent** that functions as a single entry point for users but internally orchestrates a team of specialized agents to solve a problem. It demonstrates how to wrap a complex CrewAI process into a standard Bindu agent interface.

### The Crew
The agent coordinates three internal sub-agents:
1.  **Intake Agent**: "The Listener" - Extracts structured data (income, credit score, goals) from natural language user input.
2.  **Rate Analyst Agent**: "The Expert" - Compares the user's profile against a deterministic local rate sheet (`rates.json`) to find the best compliant offers.
3.  **Compliance Agent**: "The Lawyer" - Reviews the final output to ensure it contains mandatory legal disclaimers ("Not financial advice") before sending it to the user.

## 🎯 What It Does
1.  **Accepts a Query**: E.g., *"I make $85k/year, 740 credit score, looking for a 30-year loan."*
2.  **Analyzes & Filters**: Uses the internal crew to parse this info and filter a mock database of mortgage rates.
3.  **Formulates a Response**: Returns a formatted response with the best rate found and a mandatory legal disclaimer.
4.  **Enforces Rules**: The Compliance Agent guarantees that no response leaves the system without the required warnings.

## 🔌 How It Connects to Bindu
The agent uses the `bindufy` decorator to transform the CrewAI logic into a **Bindu Agent**.
-   **Identity**: It gets a DID (Decentralized Identifier) and a unique Agent ID.
-   **API**: Bindu exposes the CrewAI logic as a standard HTTP API (`/api/v1/agent/run`).
-   **Discoverability**: It generates an Agent Card metadata file.
-   **Extensibility**: By being a Bindu agent, it can easily add **Payments (x402)**, **Authentication**, or **Remote Storage** in the future just by updating the config.

## 🚀 Usage

### Prerequisites
- Python 3.10+
- `crewai` (optional - a mock implementation is provided if installation fails)

### Quick Start
Use the runner script to start the agent:
```bash
python run_mortgage_agent.py
```
*Note: We use a runner script to correct Python path issues with the `bindu` package.*

The agent will start on `http://localhost:3775`.

### Example Query
```bash
curl -X POST http://localhost:3775/ \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "I make $90,000, 750 credit score, 15 year term"}]}'
```
