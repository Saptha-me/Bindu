import json
import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

class AuditLogger:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.log_file = os.path.join(log_dir, "audit_log.json")
        
        # We use a standard logger but ensure it's append-only and structured
        self.logger = logging.getLogger("AuditLogger")
        self.logger.setLevel(logging.INFO)
        
        # Append-only handler
        handler = RotatingFileHandler(self.log_file, maxBytes=10*1024*1024, backupCount=5)
        self.logger.addHandler(handler)

    def log_decision(self, session_id, role, input_query, recommendation, confidence_score, sources):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "audit_id": f"audit_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            "session_id": session_id,
            "role": role,
            "input_query": input_query,
            "recommendation": recommendation,
            "confidence_score": confidence_score,
            "sources_used": sources
        }
        
        self.logger.info(json.dumps(log_entry))
        return log_entry["audit_id"]

if __name__ == "__main__":
    # Test logger
    logger = AuditLogger(".")
    aid = logger.log_decision("test_sess", "clinician", "test query", "test rec", 0.95, ["source1"])
    print(f"Logged with ID: {aid}")
