import random
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

def generate_synthetic_data(n_samples: int = 5000) -> List[Dict[str, Any]]:
    """
    Generates balanced synthetic labeled API records for Random Forest training.
    Labels derived from the same rules as api_inventory.json categories.
    """
    random.seed(42)
    categories = ["active", "deprecated", "orphaned", "zombie", "shadow"]
    samples_per_category = n_samples // len(categories)
    dataset = []

    now = datetime.now(timezone.utc)

    def _iso(days_ago: int) -> str:
        if days_ago == 9999:
            return None
        return (now - timedelta(days=days_ago)).isoformat()

    for category in categories:
        for _ in range(samples_per_category):
            api = {
                "endpoint": f"/mock/{category}/{random.randint(1000, 9999)}",
                "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                "last_called_at": None,
                "last_deployment_at": None,
                "call_volume_30d": 0,
                "call_volume_7d": 0,
                "error_rate": 0.0,
                "response_time_p95_ms": 200,
                "has_auth": True,
                "has_encryption": True,
                "has_rate_limit": True,
                "has_documentation": True,
                "is_documented_in_gateway": True,
                "version_age_days": 30,
                "dependent_services_count": 5,
                "response_time_trend": 0,
                "data_sensitivity": "low",
                "owner_team": "mock-team",
                "consecutive_error_days": 0,
                "unique_callers_30d": 50,
                "source": "api_gateway"
            }
            
            # Apply category-specific rules
            if category == "active":
                api["last_called_at"] = _iso(random.randint(0, 5))
                api["last_deployment_at"] = _iso(random.randint(10, 60))
                api["call_volume_30d"] = random.randint(5000, 50000)
                api["error_rate"] = random.uniform(0.0, 0.02)
                api["is_documented_in_gateway"] = True
                
            elif category == "deprecated":
                api["last_called_at"] = _iso(random.randint(5, 30))
                api["last_deployment_at"] = _iso(random.randint(200, 400))
                api["call_volume_30d"] = random.randint(100, 1000)
                api["error_rate"] = random.uniform(0.1, 0.3)
                api["version_age_days"] = random.randint(300, 600)
                api["response_time_trend"] = 1
                
            elif category == "orphaned":
                api["owner_team"] = None
                api["has_documentation"] = False
                api["last_called_at"] = _iso(random.randint(1, 10))
                api["call_volume_30d"] = random.randint(50, 500)
                api["dependent_services_count"] = 0
                api["is_documented_in_gateway"] = False
                api["source"] = "code_repository"
                
            elif category == "zombie":
                api["last_called_at"] = _iso(random.randint(180, 1000))
                api["last_deployment_at"] = _iso(random.randint(500, 1500))
                api["call_volume_30d"] = random.randint(0, 4)
                api["has_auth"] = False
                api["has_documentation"] = False
                api["is_documented_in_gateway"] = False
                api["owner_team"] = None
                api["source"] = "legacy_system"
                api["error_rate"] = random.uniform(0.4, 0.9)
                
            elif category == "shadow":
                api["last_called_at"] = _iso(random.randint(0, 2))
                api["call_volume_30d"] = random.randint(1000, 20000)
                api["has_auth"] = random.choice([True, False])
                api["is_documented_in_gateway"] = False
                api["has_documentation"] = False
                api["source"] = "network_probe"
                
            api["meta_label"] = category
            dataset.append(api)

    random.shuffle(dataset)
    return dataset
