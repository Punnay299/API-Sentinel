-- ================================================================
-- FILE: database/schema.sql
-- Run once at startup via: sqlite3 zombieguard.db < schema.sql
-- ================================================================

PRAGMA journal_mode = WAL;   -- Enable Write-Ahead Logging for concurrency
PRAGMA foreign_keys = ON;    -- Enforce FK constraints

-- ────────────────────────────────────────────────────────────────
-- TABLE: apis
-- Core registry of all discovered API endpoints
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS apis (
    id                      TEXT    PRIMARY KEY,          -- e.g. "api-001"
    endpoint                TEXT    NOT NULL,             -- "/api/v3/payments"
    method                  TEXT    NOT NULL DEFAULT 'GET',  -- GET|POST|PUT|DELETE
    version                 TEXT,                         -- "v3"
    owner_team              TEXT,                         -- "payments-team" or NULL
    source                  TEXT    NOT NULL,             -- "api_gateway"|"legacy_system"|"internal_probe"
    tags                    TEXT    DEFAULT '[]',         -- JSON array: ["legacy","zombie-candidate"]
    
    -- Traffic metrics
    last_called_at          TEXT,                         -- ISO 8601 timestamp
    last_deployment_at      TEXT,                         -- ISO 8601 timestamp
    call_volume_30d         INTEGER DEFAULT 0,
    call_volume_7d          INTEGER DEFAULT 0,
    error_rate              REAL    DEFAULT 0.0,          -- 0.0 to 1.0
    response_time_p95_ms    INTEGER DEFAULT 0,
    unique_callers_30d      INTEGER DEFAULT 0,
    consecutive_error_days  INTEGER DEFAULT 0,

    -- Security posture flags
    has_auth                INTEGER DEFAULT 0,            -- 0=false, 1=true
    has_encryption          INTEGER DEFAULT 1,
    has_rate_limit          INTEGER DEFAULT 0,
    has_documentation       INTEGER DEFAULT 0,
    is_documented_in_gateway INTEGER DEFAULT 0,

    -- API characteristics
    version_age_days        INTEGER DEFAULT 0,
    dependent_services_count INTEGER DEFAULT 0,
    response_time_trend     INTEGER DEFAULT 0,            -- -1=improving, 0=stable, 1=degrading
    data_sensitivity        TEXT    DEFAULT 'low',        -- none|low|medium|high|pii|financial

    -- ML Classification Results (written after each analysis)
    ml_status               TEXT    DEFAULT 'unknown',    -- active|deprecated|orphaned|zombie|shadow
    ml_confidence           REAL    DEFAULT 0.0,
    ml_probabilities        TEXT    DEFAULT '{}',         -- JSON: {"zombie": 0.94, "active": 0.02, ...}
    ml_security_score       INTEGER DEFAULT 0,            -- 0-100
    ml_risk_level           TEXT    DEFAULT 'unknown',    -- low|medium|high|critical
    ml_security_issues      TEXT    DEFAULT '[]',         -- JSON array of issue objects
    ml_is_shadow            INTEGER DEFAULT 0,
    ml_anomaly_score        REAL    DEFAULT 0.0,
    ml_analyzed_at          TEXT,                         -- ISO timestamp of last ML run

    -- Lifecycle
    discovered_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    is_active               INTEGER DEFAULT 1,
    decommissioned_at       TEXT
);

CREATE INDEX IF NOT EXISTS idx_apis_ml_status  ON apis(ml_status);
CREATE INDEX IF NOT EXISTS idx_apis_ml_risk    ON apis(ml_risk_level);
CREATE INDEX IF NOT EXISTS idx_apis_owner      ON apis(owner_team);
CREATE INDEX IF NOT EXISTS idx_apis_source     ON apis(source);


-- ────────────────────────────────────────────────────────────────
-- TABLE: scans
-- Each network scan session
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scans (
    id          TEXT    PRIMARY KEY,
    status      TEXT    NOT NULL DEFAULT 'pending',   -- pending|running|completed|failed
    targets     TEXT    DEFAULT '[]',                 -- JSON: ["api_gateway","github","k8s"]
    deep_scan   INTEGER DEFAULT 0,
    apis_found  INTEGER DEFAULT 0,
    progress    INTEGER DEFAULT 0,                    -- 0-100
    started_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    error_msg   TEXT
);


-- ────────────────────────────────────────────────────────────────
-- TABLE: scan_events
-- Individual events emitted during a scan (for SSE streaming)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scan_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id     TEXT    NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    event_type  TEXT    NOT NULL,   -- info|warn|critical|found|success
    source      TEXT,               -- "API Gateway"|"GitHub"|"Kubernetes"
    message     TEXT    NOT NULL,
    apis_found  INTEGER DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scan_events_scan_id ON scan_events(scan_id);


-- ────────────────────────────────────────────────────────────────
-- TABLE: api_metrics
-- Time-series traffic data per API (for trend charts)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    api_id          TEXT    NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    recorded_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    call_count      INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    p95_latency_ms  INTEGER DEFAULT 0,
    unique_callers  INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_metrics_api_id    ON api_metrics(api_id);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded  ON api_metrics(recorded_at);


-- ────────────────────────────────────────────────────────────────
-- TABLE: decomm_workflows
-- Tracks decommissioning state machine per API
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decomm_workflows (
    id              TEXT    PRIMARY KEY,          -- UUID
    api_id          TEXT    NOT NULL UNIQUE REFERENCES apis(id),
    status          TEXT    NOT NULL DEFAULT 'pending',   -- pending|in_progress|completed|aborted
    current_step    TEXT,
    completed_steps TEXT    DEFAULT '[]',         -- JSON array of completed step IDs
    initiated_by    TEXT    DEFAULT 'system',
    started_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at    TEXT,
    notes           TEXT
);


-- ────────────────────────────────────────────────────────────────
-- TABLE: security_issues
-- Normalised security findings per API
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS security_issues (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api_id      TEXT    NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    issue_type  TEXT    NOT NULL,   -- auth|encrypt|ratelimit|docs|ownership|data
    severity    TEXT    NOT NULL,   -- critical|high|medium|low
    message     TEXT    NOT NULL,
    is_resolved INTEGER DEFAULT 0,
    detected_at TEXT    NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_issues_api_id   ON security_issues(api_id);
CREATE INDEX IF NOT EXISTS idx_issues_severity ON security_issues(severity);


-- ────────────────────────────────────────────────────────────────
-- TABLE: alerts
-- Real-time alert feed (pushed via WebSocket)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api_id      TEXT    REFERENCES apis(id) ON DELETE SET NULL,
    alert_type  TEXT    NOT NULL,   -- ZOMBIE|SHADOW|ORPHAN|SECFAIL|SCAN_COMPLETE
    severity    TEXT    NOT NULL DEFAULT 'medium',
    message     TEXT    NOT NULL,
    is_read     INTEGER DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unread  ON alerts(is_read) WHERE is_read = 0;


-- ────────────────────────────────────────────────────────────────
-- TABLE: ml_models
-- Model version registry and performance metrics
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml_models (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_type      TEXT    NOT NULL,   -- classifier|shadow_detector|risk_scorer
    version         TEXT    NOT NULL,
    accuracy        REAL,
    f1_score        REAL,
    training_samples INTEGER,
    trained_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    model_path      TEXT,
    is_active       INTEGER DEFAULT 1
);


-- ────────────────────────────────────────────────────────────────
-- TABLE: audit_log
-- Immutable record of all user actions (compliance)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    actor       TEXT    NOT NULL DEFAULT 'system',
    action      TEXT    NOT NULL,   -- "decommission_started"|"api_suppressed"|"scan_initiated"
    entity_type TEXT,               -- "api"|"scan"|"workflow"
    entity_id   TEXT,
    details     TEXT    DEFAULT '{}',   -- JSON
    ip_address  TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
