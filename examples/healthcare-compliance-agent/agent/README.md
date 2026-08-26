# Bindu Healthcare Compliance Agent

A compliance-first clinical decision support prototype built on the Bindu "Internet of Agents" platform.

## Features
- **A2A Compliant**: Seamlessly integrates into Bindu ecosystems.
- **Evidence-Linked**: Every suggestion links back to verified clinical protocols.
- **Confidence Scoring**: Explicitly communicates uncertainty (Uncertainty Flag + Confidence Score).
- **Immutable Audit Trail**: Logs every decision to a tamper-evident JSON vault.
- **Role-Based Reasoning**: Tailored responses for Clinicians, Nurses, and Patients.

## Setup & Usage

### Prerequisites
- Python 3.12+
- `bindu` package (install via `pip install bindu`)
- `pytest` for testing

### Running the Agent
```bash
python agent.py
```
The agent starts on port **3773**.

### Example Query (cURL)
```bash
curl -X POST http://localhost:3773/messages \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "demo_123",
       "role": "clinician",
       "content": "What is the starting dose for Lisinopril?"
     }'
```

### Running Tests
```bash
pytest tests/test_agent.py
```

## Technical Architecture
- **Retriever**: Keyword-based RAG matching against `guidelines/`.
- **Calibrator**: Scores matches (High/Low) and flags uncertainty if score < 0.7.
- **Logger**: Append-only rotating JSON logs in `logs/audit_log.json`.
