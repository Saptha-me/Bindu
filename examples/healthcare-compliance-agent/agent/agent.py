import os
import json
from evidence_retriever import EvidenceRetriever
from confidence_calibrator import ConfidenceCalibrator
from audit_logger import AuditLogger

try:
    from bindu.penguin.bindufy import bindufy
    HAS_BINDU = True
except ImportError:
    HAS_BINDU = False

# Initialize modules
GUIDELINES_DIR = os.path.join(os.path.dirname(__file__), "guidelines")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

retriever = EvidenceRetriever(GUIDELINES_DIR)
calibrator = ConfidenceCalibrator(threshold=0.7)
logger = AuditLogger(LOG_DIR)

AGENT_CONFIG = {
    "name": "Healthcare Compliance Agent",
    "author": "Antigravity",
    "description": "A compliance-first agent for clinical decision support with evidence linking.",
    "version": "1.0.0",
    "deployment": {
        "port": 3773
    },
    "skills": [
        {
            "name": "clinical-decision-support",
            "description": "Provides recommendations grounded in clinical guidelines."
        },
        {
            "name": "compliance-check",
            "description": "Verifies recommendations against institutional protocols."
        },
        {
            "name": "evidence-retrieval",
            "description": "Retrieves specific guideline snippets for queries."
        }
    ]
}

def healthcare_agent_handler(payload):
    """
    Main handler for A2A messages.
    Payload expected structure:
    {
        "session_id": "...",
        "role": "clinician|nurse|patient",
        "content": "..."
    }
    """
    try:
        # Extract data from A2A payload
        session_id = payload.get("session_id", "unknown_session")
        role = payload.get("role", "patient").lower()
        query = payload.get("content", "")

        # 1. Retrieve Evidence
        matches = retriever.retrieve(query)

        # 2. Calibrate Confidence
        confidence_score, uncertainty_flag = calibrator.calibrate(query, matches)

        # 3. Generate Recommendation (Grounding)
        if not matches:
            recommendation = "I could not find a specific institutional guideline matching your query. Please consult a senior clinician or refer to the latest medical standards."
            sources = []
        else:
            top_match = matches[0]
            sources = [f"{top_match['source']}: {top_match['title']}"]
            
            if role == "clinician":
                recommendation = f"Based on {top_match['title']}: {top_match['snippet'][:500]}..."
            elif role == "nurse":
                recommendation = f"Instruction for Nursing Staff (per {top_match['source']}): Focus on monitoring parameters and escalation thresholds. Key snippet: {top_match['snippet'][:300]}..."
            else: # patient
                recommendation = f"General Information: {top_match['title']} suggests following professional guidance. Snippet: {top_match['snippet'][:200]}... [Note: Always consult your doctor for medical advice.]"

        # 4. Human Review Flag
        human_review_recommended = confidence_score < 0.7

        # 5. Audit Logging
        audit_id = logger.log_decision(
            session_id=session_id,
            role=role,
            input_query=query,
            recommendation=recommendation,
            confidence_score=confidence_score,
            sources=sources
        )

        return {
            "content": recommendation,
            "sources": sources,
            "confidence_score": confidence_score,
            "uncertainty_flag": uncertainty_flag,
            "human_review_recommended": human_review_recommended,
            "role_context": role,
            "audit_id": audit_id
        }

    except Exception as e:
        return {
            "error": f"Internal selection error: {str(e)}",
            "audit_id": None
        }

if __name__ == "__main__":
    if HAS_BINDU:
        bindufy(None, AGENT_CONFIG, healthcare_agent_handler)
    else:
        print("!!! [DEMO MODE] Bindu framework not found. Running in Standalone Demo Mode. !!!\n")
        
        test_payloads = [
            {
                "role": "clinician",
                "content": "What is the starting dose for Lisinopril for hypertension?"
            },
            {
                "role": "patient",
                "content": "How to treat diabetes?"
            }
        ]

        for i, payload in enumerate(test_payloads):
            print(f"--- [REQUEST {i+1}] (Role: {payload['role']}) ---")
            print(f"Query: {payload['content']}")
            response = healthcare_agent_handler(payload)
            print(f"\n[RESPONSE]")
            print(f"Recommendation: {response.get('content')}")
            print(f"Sources: {response.get('sources')}")
            print(f"Confidence: {response.get('confidence_score')} (Uncertainty: {response.get('uncertainty_flag')})")
            print(f"Audit ID: {response.get('audit_id')}")
            print("-" * 50 + "\n")
        
        print(f"Check logs in: {LOG_DIR}")
