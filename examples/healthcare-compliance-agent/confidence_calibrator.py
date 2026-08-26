class ConfidenceCalibrator:
    def __init__(self, threshold=0.7):
        self.threshold = threshold

    def calibrate(self, query, matches):
        """
        Calculates a confidence score based on the strength of evidence.
        """
        if not matches:
            return 0.0, True # confidence, uncertainty_flag

        # Simplified logic: 
        # - Max relevance score from matches
        # - Penalize if query is very long and match is weak
        max_relevance = max(m["relevance_score"] for m in matches)
        
        # Heuristic: if we have a match with at least 3 keyword overlaps, confidence is high
        if max_relevance >= 3:
            score = 0.95
        elif max_relevance >= 2:
            score = 0.75
        elif max_relevance >= 1:
            score = 0.5
        else:
            score = 0.3
            
        uncertainty_flag = score < self.threshold
        
        return score, uncertainty_flag

if __name__ == "__main__":
    # Test calibrator
    calibrator = ConfidenceCalibrator()
    s, f = calibrator.calibrate("hypertension treatment", [{"relevance_score": 4}])
    print(f"Score: {s}, Uncertain: {f}")
