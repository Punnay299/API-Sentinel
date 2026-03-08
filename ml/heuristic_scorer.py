class HeuristicScorer:
    """
    Pure Python rule-based evaluation engine replacing Gradient Boosting.
    Evaluates api_dict to deduce security risk natively on the event loop.
    """

    def score(self, api_dict: dict) -> dict:
        score = 100
        deductions = []

        # 1. Authentication Check
        if not api_dict.get("has_auth", False):
            score -= 30
            deductions.append("-30: Missing Authentication")

        # 2. Encryption Check
        if not api_dict.get("has_encryption", True):
            score -= 20
            deductions.append("-20: Missing TLS/Encryption")

        # 3. Rate Limiting
        if not api_dict.get("has_rate_limit", False):
            score -= 10
            deductions.append("-10: Missing Rate Limiting")

        # 4. Ownership
        if not api_dict.get("owner_team"):
            score -= 15
            deductions.append("-15: Orphaned (No Owner Assigned)")

        # 5. Gateway Registration
        if not api_dict.get("is_documented_in_gateway", False):
            score -= 15
            deductions.append("-15: Shadow API (Not in API Gateway)")

        # 6. Error Rate anomalies
        error_rate = api_dict.get("error_rate", 0.0)
        if error_rate > 0.1:
            penalty = min(20, int((error_rate - 0.1) * 100))
            score -= penalty
            deductions.append(f"-{penalty}: High Error Rate ({error_rate:.1%})")

        # 7. Sensitive Data Penalty (Multiplier effect on bad posture)
        sensitivity = api_dict.get("data_sensitivity", "low").lower()
        if sensitivity in ["high", "pii", "financial"] and score < 70:
            score -= 10
            deductions.append("-10: High Sensitivity Data with Poor Posture")

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        # Determine Risk Level
        if score >= 80:
            risk_level = "low"
        elif score >= 60:
            risk_level = "medium"
        elif score >= 40:
            risk_level = "high"
        else:
            risk_level = "critical"

        return {
            "security_score": score,
            "risk_level": risk_level,
            "deductions": deductions
        }
