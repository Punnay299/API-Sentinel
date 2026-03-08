from datetime import datetime, timezone
from typing import Optional

SENSITIVITY_MAP = {
    "none": 0, "low": 1, "medium": 2,
    "high": 3, "pii": 3, "financial": 3,
}

FEATURE_COLS = [
    "days_since_last_call",
    "call_volume_30d",
    "call_volume_7d",
    "error_rate",
    "response_time_p95_ms",
    "has_auth",
    "has_encryption",
    "has_rate_limit",
    "has_documentation",
    "version_age_days",
    "dependent_services_count",
    "response_time_trend",
    "data_sensitivity_score",
    "owner_assigned",
    "is_documented_in_gateway",
    "consecutive_error_days",
    "unique_callers_30d",
    "last_deployment_days"
]

def _days_ago(iso_str: Optional[str]) -> int:
    """Parse ISO timestamp and return days elapsed. Returns 9999 if missing."""
    if not iso_str:
        return 9999
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)
    except (ValueError, TypeError):
        return 9999

def extract_features(api: dict) -> list[float]:
    """
    Convert raw API metadata dict -> 18-element float list.
    Order must exactly match FEATURE_COLS.
    """
    return [
        float(_days_ago(api.get("last_called_at"))),
        float(api.get("call_volume_30d", 0)),
        float(api.get("call_volume_7d", 0)),
        float(api.get("error_rate", 0.0)),
        float(api.get("response_time_p95_ms", 500)),
        float(int(bool(api.get("has_auth", False)))),
        float(int(bool(api.get("has_encryption", False)))),
        float(int(bool(api.get("has_rate_limit", False)))),
        float(int(bool(api.get("has_documentation", False)))),
        float(api.get("version_age_days", 0)),
        float(api.get("dependent_services_count", 0)),
        float(api.get("response_time_trend", 0)),
        float(SENSITIVITY_MAP.get(api.get("data_sensitivity", "low"), 1)),
        float(int(bool(api.get("owner_team")))),
        float(int(bool(api.get("is_documented_in_gateway", False)))),
        float(api.get("consecutive_error_days", 0)),
        float(api.get("unique_callers_30d", 0)),
        float(_days_ago(api.get("last_deployment_at"))),
    ]
