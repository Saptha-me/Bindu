import pytest
import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from evidence_retriever import EvidenceRetriever
from confidence_calibrator import ConfidenceCalibrator
from audit_logger import AuditLogger
from agent import healthcare_agent_handler

def test_retriever():
    # Note: assumed to be run from project root or test dir
    retriever = EvidenceRetriever("guidelines")
    results = retriever.retrieve("hypertension diagnosis")
    assert len(results) > 0
    assert "HYPERTENSION_MGMT_001" in [r["source"] for r in results]

def test_calibrator():
    calibrator = ConfidenceCalibrator()
    score, flag = calibrator.calibrate("test", [{"relevance_score": 5}])
    assert score == 0.95
    assert flag is False
    
    score_low, flag_low = calibrator.calibrate("test", [])
    assert score_low == 0.0
    assert flag_low is True

def test_audit_logger(tmp_path):
    log_dir = tmp_path / "logs"
    logger = AuditLogger(str(log_dir))
    aid = logger.log_decision("s1", "clinician", "q", "r", 0.9, ["src"])
    assert aid.startswith("audit_")
    
    log_file = log_dir / "audit_log.json"
    assert log_file.exists()
    with open(log_file, "r") as f:
        log_content = f.read()
        assert "clinician" in log_content

def test_agent_handler_clinician():
    payload = {
        "session_id": "test_clinician",
        "role": "clinician",
        "content": "How to treat diabetes?"
    }
    response = healthcare_agent_handler(payload)
    assert response["role_context"] == "clinician"
    assert "DIABETES_T2_MGMT_002" in response["sources"][0]
    assert response["confidence_score"] >= 0.7

def test_agent_handler_patient():
    payload = {
        "session_id": "test_patient",
        "role": "patient",
        "content": "Lisinopril dose?"
    }
    response = healthcare_agent_handler(payload)
    assert "Always consult your doctor" in response["content"]
    assert response["role_context"] == "patient"
