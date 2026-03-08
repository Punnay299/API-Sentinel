import json
import random
from datetime import datetime, timedelta, timezone

random.seed(42)  # Always produces the same output

def now():
    return datetime.now(timezone.utc)

def days_ago(n):
    return (now() - timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%SZ")

def rand_between(a, b):
    return random.randint(a, b)

def rand_float(a, b, decimals=3):
    return round(random.uniform(a, b), decimals)

def rand_bool(true_probability):
    return random.random() < true_probability


# ──────────────────────────────────────────────────────────────
# DEFINE ALL 45 APIs
# Each tuple: (endpoint, method, category, owner_team)
# category drives how "sick" the API is
# ──────────────────────────────────────────────────────────────

APIs = [
    # ── HEALTHY ACTIVE APIs (14) ──────────────────────────────
    ("/api/v3/payments",             "POST",  "active",     "payments-team"),
    ("/api/v3/transfers",            "POST",  "active",     "payments-team"),
    ("/api/v3/biometrics/verify",    "POST",  "active",     "auth-team"),
    ("/api/v3/auth/token",           "POST",  "active",     "auth-team"),
    ("/api/v2/accounts/balance",     "GET",   "active",     "core-banking"),
    ("/api/v2/cards/list",           "GET",   "active",     "card-service"),
    ("/api/v3/analytics/dashboard",  "GET",   "active",     "data-platform"),
    ("/api/v2/loans/apply",          "POST",  "active",     "lending-team"),
    ("/api/v3/crypto/prices",        "GET",   "active",     "crypto-team"),
    ("/api/v2/portfolio/summary",    "GET",   "active",     "wealth-team"),
    ("/api/v2/rewards/points",       "GET",   "active",     "loyalty-team"),
    ("/api/v3/webhooks/register",    "POST",  "active",     "platform-team"),
    ("/api/v2/support/ticket",       "POST",  "active",     "crm-team"),
    ("/api/v1/notifications/push",   "POST",  "active",     "notification-team"),

    # ── DEPRECATED APIs (5) ───────────────────────────────────
    ("/api/v1/payments",             "POST",  "deprecated", "payments-team"),
    ("/api/v1/accounts",             "GET",   "deprecated", "core-banking"),
    ("/api/v1/auth/login",           "POST",  "deprecated", "auth-team"),
    ("/api/v1/cards",                "GET",   "deprecated", "card-service"),
    ("/api/v1/loans",                "POST",  "deprecated", "lending-team"),

    # ── ORPHANED APIs (5) ─────────────────────────────────────
    ("/api/v2/investment/history",   "GET",   "orphaned",   None),
    ("/api/v1/kyc/status",           "GET",   "orphaned",   None),
    ("/api/v2/forex/convert",        "POST",  "orphaned",   None),
    ("/api/v1/beneficiaries/list",   "GET",   "orphaned",   None),
    ("/api/v2/budget/analysis",      "GET",   "orphaned",   None),

    # ── ZOMBIE APIs (7) ───────────────────────────────────────
    ("/legacy/v1/accounts",          "GET",   "zombie",     None),
    ("/legacy/v1/balances",          "GET",   "zombie",     None),
    ("/legacy/v2/transactions",      "GET",   "zombie",     None),
    ("/legacy/v1/auth",              "POST",  "zombie",     None),
    ("/legacy/v2/forex",             "GET",   "zombie",     None),
    ("/legacy/v3/statements",        "GET",   "zombie",     None),
    ("/legacy/v1/reports/monthly",   "GET",   "zombie",     None),

    # ── SHADOW APIs (9) ───────────────────────────────────────
    ("/internal/admin/users",        "GET",   "shadow",     None),
    ("/internal/audit/logs",         "GET",   "shadow",     None),
    ("/internal/compliance/check",   "POST",  "shadow",     None),
    ("/internal/ml/scoring",         "POST",  "shadow",     None),
    ("/internal/cache/flush",        "POST",  "shadow",     None),
    ("/internal/log/aggregator",     "GET",   "shadow",     None),
    ("/internal/reports/daily",      "GET",   "shadow",     None),
    ("/internal/batch/processor",    "POST",  "shadow",     None),
    ("/internal/user/impersonate",   "POST",  "shadow",     None),

    # ── BORDERLINE (could go either way — keeps ML honest) ────
    ("/api/v2/merchants/onboard",    "POST",  "active",     "acquiring-team"),
    ("/api/v1/otp/verify",           "POST",  "active",     "auth-team"),
    ("/api/v1/limits/check",         "GET",   "active",     "risk-team"),
    ("/api/v2/statements/download",  "GET",   "deprecated", "core-banking"),
    ("/api/v1/preferences/update",   "PUT",   "orphaned",   None),
]


# ──────────────────────────────────────────────────────────────
# GENERATORS PER CATEGORY
# These produce realistic raw telemetry — no "status" field
# ──────────────────────────────────────────────────────────────

def make_active(endpoint, method, owner):
    volume_30d = rand_between(800, 25000)
    return {
        "endpoint":                 endpoint,
        "method":                   method,
        "owner_team":               owner,
        "last_called_at":           days_ago(rand_between(0, 6)),
        "last_deployment_at":       days_ago(rand_between(5, 90)),
        "call_volume_30d":          volume_30d,
        "call_volume_7d":           rand_between(int(volume_30d * 0.2), int(volume_30d * 0.3)),
        "error_rate":               rand_float(0.001, 0.04),
        "response_time_p95_ms":     rand_between(40, 350),
        "has_auth":                 rand_bool(0.95),
        "has_encryption":           rand_bool(0.98),
        "has_rate_limit":           rand_bool(0.80),
        "has_documentation":        rand_bool(0.85),
        "is_documented_in_gateway": rand_bool(0.92),
        "version_age_days":         rand_between(10, 180),
        "dependent_services_count": rand_between(2, 15),
        "response_time_trend":      random.choice([-1, 0, 0, 0]),   # mostly stable/improving
        "data_sensitivity":         random.choice(["low", "medium", "high", "financial"]),
        "consecutive_error_days":   rand_between(0, 2),
        "unique_callers_30d":       rand_between(10, 200),
        "source":                   "api_gateway",
        "tags":                     ["managed", "v3"],
    }


def make_deprecated(endpoint, method, owner):
    volume_30d = rand_between(20, 300)
    return {
        "endpoint":                 endpoint,
        "method":                   method,
        "owner_team":               owner,
        "last_called_at":           days_ago(rand_between(20, 80)),
        "last_deployment_at":       days_ago(rand_between(200, 500)),
        "call_volume_30d":          volume_30d,
        "call_volume_7d":           rand_between(0, int(volume_30d * 0.15)),
        "error_rate":               rand_float(0.08, 0.28),
        "response_time_p95_ms":     rand_between(400, 1800),
        "has_auth":                 rand_bool(0.70),
        "has_encryption":           rand_bool(0.75),
        "has_rate_limit":           rand_bool(0.50),
        "has_documentation":        rand_bool(0.55),
        "is_documented_in_gateway": rand_bool(0.60),
        "version_age_days":         rand_between(300, 700),
        "dependent_services_count": rand_between(0, 4),
        "response_time_trend":      random.choice([0, 1, 1]),       # mostly degrading
        "data_sensitivity":         random.choice(["low", "medium", "pii"]),
        "consecutive_error_days":   rand_between(3, 15),
        "unique_callers_30d":       rand_between(1, 20),
        "source":                   "api_gateway",
        "tags":                     ["v1", "sunset-pending"],
    }


def make_orphaned(endpoint, method, owner):
    volume_30d = rand_between(5, 200)
    return {
        "endpoint":                 endpoint,
        "method":                   method,
        "owner_team":               None,               # Key signal: no owner
        "last_called_at":           days_ago(rand_between(25, 120)),
        "last_deployment_at":       days_ago(rand_between(100, 400)),
        "call_volume_30d":          volume_30d,
        "call_volume_7d":           rand_between(0, int(volume_30d * 0.1)),
        "error_rate":               rand_float(0.05, 0.20),
        "response_time_p95_ms":     rand_between(200, 2000),
        "has_auth":                 rand_bool(0.40),    # Often missing
        "has_encryption":           rand_bool(0.55),
        "has_rate_limit":           rand_bool(0.30),
        "has_documentation":        rand_bool(0.25),    # Usually no docs
        "is_documented_in_gateway": False,              # Never in gateway
        "version_age_days":         rand_between(120, 500),
        "dependent_services_count": 0,                  # No dependents
        "response_time_trend":      random.choice([0, 1]),
        "data_sensitivity":         random.choice(["medium", "high", "pii"]),
        "consecutive_error_days":   rand_between(0, 10),
        "unique_callers_30d":       rand_between(0, 8),
        "source":                   "code_repository",
        "tags":                     ["no-owner", "unregistered"],
    }


def make_zombie(endpoint, method, owner):
    return {
        "endpoint":                 endpoint,
        "method":                   method,
        "owner_team":               None,
        "last_called_at":           days_ago(rand_between(200, 600)),  # Very stale
        "last_deployment_at":       days_ago(rand_between(400, 1200)),
        "call_volume_30d":          rand_between(0, 4),                # Near zero
        "call_volume_7d":           0,
        "error_rate":               rand_float(0.25, 0.75),            # High errors
        "response_time_p95_ms":     rand_between(1500, 6000),
        "has_auth":                 False,
        "has_encryption":           rand_bool(0.20),
        "has_rate_limit":           False,
        "has_documentation":        False,
        "is_documented_in_gateway": False,
        "version_age_days":         rand_between(500, 1500),
        "dependent_services_count": 0,
        "response_time_trend":      1,                                 # Always degrading
        "data_sensitivity":         random.choice(["financial", "pii", "high"]),
        "consecutive_error_days":   rand_between(10, 45),
        "unique_callers_30d":       0,
        "source":                   "legacy_system",
        "tags":                     ["legacy", "no-auth", "stale"],
    }


def make_shadow(endpoint, method, owner):
    volume_30d = rand_between(100, 2000)  # Active but invisible
    return {
        "endpoint":                 endpoint,
        "method":                   method,
        "owner_team":               None,
        "last_called_at":           days_ago(rand_between(0, 3)),      # Recently active
        "last_deployment_at":       days_ago(rand_between(10, 180)),
        "call_volume_30d":          volume_30d,
        "call_volume_7d":           rand_between(int(volume_30d * 0.2), int(volume_30d * 0.3)),
        "error_rate":               rand_float(0.00, 0.06),
        "response_time_p95_ms":     rand_between(50, 500),
        "has_auth":                 False,                             # No auth — key signal
        "has_encryption":           rand_bool(0.45),
        "has_rate_limit":           False,                             # No rate limit
        "has_documentation":        False,                             # No docs — key signal
        "is_documented_in_gateway": False,                             # Not in gateway
        "version_age_days":         rand_between(0, 150),
        "dependent_services_count": rand_between(1, 8),
        "response_time_trend":      random.choice([-1, 0]),
        "data_sensitivity":         random.choice(["pii", "financial", "high"]),
        "consecutive_error_days":   rand_between(0, 2),
        "unique_callers_30d":       rand_between(2, 40),
        "source":                   "network_probe",
        "tags":                     ["internal", "unregistered", "shadow-risk"],
    }


GENERATORS = {
    "active":     make_active,
    "deprecated": make_deprecated,
    "orphaned":   make_orphaned,
    "zombie":     make_zombie,
    "shadow":     make_shadow,
}


# ──────────────────────────────────────────────────────────────
# GENERATE
# ──────────────────────────────────────────────────────────────

def generate():
    records = []
    for i, (endpoint, method, category, owner) in enumerate(APIs):
        generator = GENERATORS[category]
        record = generator(endpoint, method, owner)

        # Add shared fields
        record["id"]           = f"api-{str(i + 1).zfill(3)}"
        record["discovered_at"] = days_ago(rand_between(0, 30))

        records.append(record)

    return records


if __name__ == "__main__":
    records = generate()

    with open("api_inventory.json", "w") as f:
        json.dump(records, f, indent=2)

    # Print summary so you can verify
    from collections import Counter
    categories = []
    for r in records:
        src = r["source"]
        auth = r["has_auth"]
        stale = r["call_volume_30d"]
        gateway = r["is_documented_in_gateway"]

        if not auth and not gateway and stale > 50:
            categories.append("shadow (likely)")
        elif r["call_volume_30d"] < 5 and not auth:
            categories.append("zombie (likely)")
        elif not r["owner_team"] and not gateway:
            categories.append("orphaned (likely)")
        else:
            categories.append("active/deprecated (likely)")

    print(f"\n✓ Generated {len(records)} API records → api_inventory.json")
    print(f"\nField coverage check:")
    print(f"  Has auth:        {sum(1 for r in records if r['has_auth'])}/{len(records)}")
    print(f"  Has encryption:  {sum(1 for r in records if r['has_encryption'])}/{len(records)}")
    print(f"  Has rate limit:  {sum(1 for r in records if r['has_rate_limit'])}/{len(records)}")
    print(f"  In gateway:      {sum(1 for r in records if r['is_documented_in_gateway'])}/{len(records)}")
    print(f"  Has owner:       {sum(1 for r in records if r['owner_team'])}/{len(records)}")
    print(f"  Zero traffic 7d: {sum(1 for r in records if r['call_volume_7d'] == 0)}/{len(records)}")
    print(f"\nSource breakdown:")
    sources = Counter(r['source'] for r in records)
    for src, count in sources.most_common():
        print(f"  {src:30s} {count}")
    print(f"\n→ Open api_inventory.json to inspect the raw records.")
