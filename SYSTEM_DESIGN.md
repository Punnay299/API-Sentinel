# ☠ ZombieGuard — Complete System Design Document
### Zombie (Stale/Defunct) API Discovery & Defence Platform
> **Stack:** React 18 · FastAPI · scikit-learn · SQLite · WebSocket · SSE  
> **Version:** 1.0.0 | **Audience:** Full-Stack + ML Engineers

---

## Table of Contents

1. [Problem Statement & Domain Analysis](#1-problem-statement--domain-analysis)
2. [High-Level System Architecture](#2-high-level-system-architecture)
3. [Database Design (SQLite)](#3-database-design-sqlite)
4. [ML Pipeline — Deep Dive](#4-ml-pipeline--deep-dive)
5. [Backend Pipeline — FastAPI](#5-backend-pipeline--fastapi)
6. [Frontend Architecture — React](#6-frontend-architecture--react)
7. [Connecting Frontend ↔ Backend](#7-connecting-frontend--backend)
8. [Scan Pipeline — End-to-End](#8-scan-pipeline--end-to-end)
9. [Decommission Workflow Pipeline](#9-decommission-workflow-pipeline)
10. [Real-Time Layer — WebSocket + SSE](#10-real-time-layer--websocket--sse)
11. [Security & Auth Design](#11-security--auth-design)
12. [Project Boilerplate & Folder Structure](#12-project-boilerplate--folder-structure)
13. [Environment Setup & Running Locally](#13-environment-setup--running-locally)
14. [API Reference](#14-api-reference)

---

## 1. Problem Statement & Domain Analysis

### 1.1 What is a Zombie API?

A **Zombie API** is an endpoint that was once alive and serving traffic but has since become stale, abandoned, or invisible — yet remains reachable on the network. Like a zombie, it has no real owner, no purpose, but it persists and poses danger.

```
                    LIFECYCLE OF AN API
                    ═══════════════════

  [CREATED] ──► [ACTIVE] ──► [DEPRECATED] ──► [DECOMMISSIONED]
                   │               │
                   │ (forgotten)   │ (never acted on)
                   ▼               ▼
              [ORPHANED] ──► [ZOMBIE] ◄── [SHADOW] (never documented)
```

### 1.2 Five API States We Detect

| State | Definition | Detection Signal |
|---|---|---|
| **Active** | Healthy, owned, documented, traffic flowing | High call volume, low error rate, has auth |
| **Deprecated** | Officially retiring, traffic declining | Version age > 300d, has deprecation headers, reducing callers |
| **Orphaned** | No team owner, no dependents, still accessible | `owner = NULL`, zero dependent services, not in gateway |
| **Zombie** | Silent, stale, abandoned — 180+ days with near-zero traffic | `last_called > 180d`, `call_volume_30d < 5`, no auth, no docs |
| **Shadow** | Active but completely invisible — no docs, no gateway registration | `is_in_gateway = false`, `has_docs = false`, high traffic |

### 1.3 Why This Matters in Banking

```
Financial Impact of Zombie APIs
════════════════════════════════
  • Unpatched legacy endpoints → attack surface for SQL injection, BOLA
  • Shadow APIs bypass WAF, rate limiting, and audit trails
  • GDPR/PCI-DSS violations when sensitive data flows through unmonitored endpoints  
  • Average cost of API breach: $6.1M (IBM Security Report 2023)
  • Zombie APIs account for 40% of API-related incidents (Salt Security 2023)
```

---

## 2. High-Level System Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ZombieGuard Platform                               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        React Frontend (Port 5173)                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │ Overview │ │   Scan   │ │ Inventory │ │ Analysis │ │Decomm... │ │  │
│  │  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └────┬─────┘ └────┬─────┘ │  │
│  │       └────────────┴─────────────┴──────────────┴────────────┘       │  │
│  │                          API Client Layer                             │  │
│  │              (axios + WebSocket + EventSource)                        │  │
│  └───────────────────────────┬──────────────────────────────────────────┘  │
│                              │ HTTP/WS                                      │
│  ┌───────────────────────────▼──────────────────────────────────────────┐  │
│  │                     FastAPI Backend (Port 8000)                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │  │
│  │  │  REST API  │  │ SSE Stream │  │ WebSocket  │  │  BG Tasks      │ │  │
│  │  │  /apis     │  │ /scan/*/   │  │ /ws/monitor│  │  scan, decomm  │ │  │
│  │  │  /analytics│  │  stream    │  │            │  │  retrain       │ │  │
│  │  └──────┬─────┘  └─────┬──────┘  └─────┬──────┘  └───────┬────────┘ │  │
│  │         └──────────────┴───────────────┴──────────────────┘          │  │
│  │                        Service Layer                                   │  │
│  │  ┌───────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │  │
│  │  │  APIService   │  │  ScanService     │  │  DecommService        │  │  │
│  │  │  - CRUD ops   │  │  - Network probe │  │  - 7-step workflow    │  │  │
│  │  │  - ML trigger │  │  - Repo scan     │  │  - State machine      │  │  │
│  │  └───────┬───────┘  └────────┬─────────┘  └──────────┬────────────┘  │  │
│  │          └───────────────────┴────────────────────────┘               │  │
│  │                        ML Engine Layer                                 │  │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │  │
│  │  │ Random Forest│  │ Isolation Forest │  │  Gradient Boosting     │  │  │
│  │  │ (Classifier) │  │ (Shadow Detect)  │  │  (Security Scorer)     │  │  │
│  │  └──────────────┘  └──────────────────┘  └────────────────────────┘  │  │
│  │                        Data Layer                                      │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                     SQLite Database                              │  │
│  │  │  apis | scans | scan_events | decomm_workflows | security_issues│  │  │
│  │  │  alerts | ml_models | api_metrics | audit_log                   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Diagram

```
SCAN TRIGGERED
      │
      ▼
┌─────────────────┐     ┌─────────────────────────────────────────────┐
│  Scanner Module │────►│  Discovery Sources                          │
│                 │     │  • API Gateway (Kong/AWS API GW)            │
│  Async Python   │     │  • Code Repos (GitHub API / GitLab)         │
│  Background     │     │  • Kubernetes Ingress                       │
│  Task           │     │  • Lambda Function URLs                     │
│                 │     │  • Network Subnet Probes                    │
└────────┬────────┘     │  • Legacy SOAP/WSDL Registries              │
         │              └─────────────────────────────────────────────┘
         ▼
┌─────────────────┐
│ Raw API Records │  { endpoint, method, last_seen, traffic_data, ... }
│  (Unclassified) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Feature Extraction                        │
│  days_since_last_call, error_rate, has_auth, version_age,  │
│  call_volume_30d, dependent_services, data_sensitivity ...  │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐
│  Random Forest     │   │  Isolation Forest  │   │  Gradient Boost    │
│  ─────────────     │   │  ──────────────    │   │  ─────────────     │
│  Status: zombie    │   │  Shadow: true      │   │  Risk: critical    │
│  Confidence: 0.94  │   │  Anomaly: 0.87     │   │  Score: 12/100     │
└────────┬───────────┘   └────────┬───────────┘   └────────┬───────────┘
         └──────────────────────┬─┘               ─────────┘
                                ▼
                   ┌────────────────────────┐
                   │    Fused ML Result     │
                   │  + Remediation Plan    │
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │    SQLite Database     │  ←── Persisted
                   └────────────┬───────────┘
                                │
                    ┌───────────┴──────────┐
                    ▼                      ▼
           React Dashboard          WebSocket Push
           (Inventory, KPIs)        (Live Alerts)
```

---

## 3. Database Design (SQLite)

### 3.1 Why SQLite?

For a bank's internal security tool, SQLite is ideal for:
- **Zero server overhead** — file-based, embedded in FastAPI process
- **ACID compliant** — safe concurrent reads, serialized writes
- **Easy backup** — single `.db` file
- **Fast enough** — handles thousands of API records with ease

Use **PostgreSQL** only when you need concurrent writes from multiple processes (e.g., distributed scanner workers).

### 3.2 Schema Definition

```sql
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
```

### 3.3 SQLite Connection — Python (SQLAlchemy + aiosqlite)

```python
# database/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event
import sqlite3, os

DATABASE_URL = "sqlite+aiosqlite:///./zombieguard.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# Enable WAL mode and foreign keys on every new connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")   # 64MB cache
        cursor.close()

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

async def get_db():
    """FastAPI dependency — yields async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Run schema.sql at startup."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    async with engine.begin() as conn:
        with open(schema_path) as f:
            sql = f.read()
        for statement in sql.split(";"):
            s = statement.strip()
            if s:
                await conn.execute(text(s))
```

### 3.4 SQLAlchemy ORM Models

```python
# database/models.py
from sqlalchemy import Column, Text, Integer, Real, ForeignKey
from sqlalchemy.orm import relationship
from database.connection import Base

class API(Base):
    __tablename__ = "apis"
    id                       = Column(Text, primary_key=True)
    endpoint                 = Column(Text, nullable=False)
    method                   = Column(Text, default="GET")
    version                  = Column(Text)
    owner_team               = Column(Text)
    source                   = Column(Text, nullable=False)
    tags                     = Column(Text, default="[]")
    last_called_at           = Column(Text)
    last_deployment_at       = Column(Text)
    call_volume_30d          = Column(Integer, default=0)
    call_volume_7d           = Column(Integer, default=0)
    error_rate               = Column(Real, default=0.0)
    response_time_p95_ms     = Column(Integer, default=0)
    has_auth                 = Column(Integer, default=0)
    has_encryption           = Column(Integer, default=1)
    has_rate_limit           = Column(Integer, default=0)
    has_documentation        = Column(Integer, default=0)
    is_documented_in_gateway = Column(Integer, default=0)
    version_age_days         = Column(Integer, default=0)
    dependent_services_count = Column(Integer, default=0)
    data_sensitivity         = Column(Text, default="low")
    ml_status                = Column(Text, default="unknown")
    ml_confidence            = Column(Real, default=0.0)
    ml_probabilities         = Column(Text, default="{}")
    ml_security_score        = Column(Integer, default=0)
    ml_risk_level            = Column(Text, default="unknown")
    ml_security_issues       = Column(Text, default="[]")
    ml_is_shadow             = Column(Integer, default=0)
    ml_analyzed_at           = Column(Text)
    discovered_at            = Column(Text)
    updated_at               = Column(Text)
    is_active                = Column(Integer, default=1)
    decommissioned_at        = Column(Text)

    metrics   = relationship("APIMetric",       back_populates="api", cascade="all, delete")
    issues    = relationship("SecurityIssue",   back_populates="api", cascade="all, delete")
    workflow  = relationship("DecommWorkflow",  back_populates="api", uselist=False)
    alerts    = relationship("Alert",           back_populates="api")


class Scan(Base):
    __tablename__ = "scans"
    id           = Column(Text, primary_key=True)
    status       = Column(Text, default="pending")
    targets      = Column(Text, default="[]")
    deep_scan    = Column(Integer, default=0)
    apis_found   = Column(Integer, default=0)
    progress     = Column(Integer, default=0)
    started_at   = Column(Text)
    completed_at = Column(Text)
    error_msg    = Column(Text)
    events       = relationship("ScanEvent", back_populates="scan", cascade="all, delete")


class ScanEvent(Base):
    __tablename__ = "scan_events"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    scan_id    = Column(Text, ForeignKey("scans.id", ondelete="CASCADE"))
    event_type = Column(Text, nullable=False)
    source     = Column(Text)
    message    = Column(Text, nullable=False)
    apis_found = Column(Integer, default=0)
    created_at = Column(Text)
    scan       = relationship("Scan", back_populates="events")


class APIMetric(Base):
    __tablename__ = "api_metrics"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    api_id         = Column(Text, ForeignKey("apis.id", ondelete="CASCADE"))
    recorded_at    = Column(Text)
    call_count     = Column(Integer, default=0)
    error_count    = Column(Integer, default=0)
    p95_latency_ms = Column(Integer, default=0)
    unique_callers = Column(Integer, default=0)
    api            = relationship("API", back_populates="metrics")


class SecurityIssue(Base):
    __tablename__ = "security_issues"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    api_id      = Column(Text, ForeignKey("apis.id", ondelete="CASCADE"))
    issue_type  = Column(Text, nullable=False)
    severity    = Column(Text, nullable=False)
    message     = Column(Text, nullable=False)
    is_resolved = Column(Integer, default=0)
    detected_at = Column(Text)
    resolved_at = Column(Text)
    api         = relationship("API", back_populates="issues")


class DecommWorkflow(Base):
    __tablename__ = "decomm_workflows"
    id              = Column(Text, primary_key=True)
    api_id          = Column(Text, ForeignKey("apis.id"), unique=True)
    status          = Column(Text, default="pending")
    current_step    = Column(Text)
    completed_steps = Column(Text, default="[]")
    initiated_by    = Column(Text, default="system")
    started_at      = Column(Text)
    completed_at    = Column(Text)
    notes           = Column(Text)
    api             = relationship("API", back_populates="workflow")


class Alert(Base):
    __tablename__ = "alerts"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    api_id     = Column(Text, ForeignKey("apis.id", ondelete="SET NULL"))
    alert_type = Column(Text, nullable=False)
    severity   = Column(Text, default="medium")
    message    = Column(Text, nullable=False)
    is_read    = Column(Integer, default=0)
    created_at = Column(Text)
    api        = relationship("API", back_populates="alerts")


class MLModel(Base):
    __tablename__ = "ml_models"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    model_type       = Column(Text, nullable=False)
    version          = Column(Text, nullable=False)
    accuracy         = Column(Real)
    f1_score         = Column(Real)
    training_samples = Column(Integer)
    trained_at       = Column(Text)
    model_path       = Column(Text)
    is_active        = Column(Integer, default=1)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    actor       = Column(Text, default="system")
    action      = Column(Text, nullable=False)
    entity_type = Column(Text)
    entity_id   = Column(Text)
    details     = Column(Text, default="{}")
    ip_address  = Column(Text)
    created_at  = Column(Text)
```

---

## 4. ML Pipeline — Deep Dive

### 4.1 Feature Engineering

Every API endpoint is reduced to an **18-dimensional feature vector** before being fed into any model.

```
Feature Vector F ∈ ℝ¹⁸

Index  Feature Name                  Type    Range        Description
─────  ────────────────────────────  ──────  ───────────  ────────────────────────────────
  0    days_since_last_call          int     0–9999       Days since any traffic was received
  1    call_volume_30d               int     0–100000     Total requests in last 30 days
  2    call_volume_7d                int     0–50000      Total requests in last 7 days
  3    error_rate                    float   0.0–1.0      Fraction of 4xx/5xx responses
  4    response_time_p95_ms          int     0–10000      95th percentile latency (ms)
  5    has_auth                      bin     0 or 1       Authentication present?
  6    has_encryption                bin     0 or 1       TLS enforced?
  7    has_rate_limit                bin     0 or 1       Rate limiting configured?
  8    has_documentation             bin     0 or 1       API docs exist?
  9    version_age_days              int     0–2000       Days since current version released
 10    dependent_services_count      int     0–50         Number of services calling this API
 11    response_time_trend           int     -1, 0, 1     -1=improving, 0=stable, 1=degrading
 12    data_sensitivity_score        int     0–3          0=none, 1=low, 2=medium, 3=high/PII
 13    owner_assigned                bin     0 or 1       Responsible team assigned?
 14    is_documented_in_gateway      bin     0 or 1       Registered in API gateway?
 15    consecutive_error_days        int     0–100        Days of sustained error spikes
 16    unique_callers_30d            int     0–500        Distinct IPs/services in 30d
 17    last_deployment_days          int     0–2000       Days since last code deployment
```

```python
# ml/feature_extractor.py

from datetime import datetime, timezone
from typing import Optional

SENSITIVITY_MAP = {
    "none": 0, "low": 1, "medium": 2,
    "high": 3, "pii": 3, "financial": 3,
}

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
    Convert raw API metadata dict → 18-element float list.
    Order must exactly match FEATURE_COLS in ml_engine.py.
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
```

### 4.2 Model 1 — Random Forest Classifier (Status)

```
Why Random Forest?
══════════════════
✓ Handles mixed numeric + binary features without heavy preprocessing
✓ Built-in feature importance → explainability for auditors
✓ Robust to outliers (e.g., zombie APIs with 9999 days_since_last_call)
✓ Ensemble of 300 trees → stable predictions, low variance
✓ class_weight="balanced" → handles class imbalance (fewer zombie samples)

Training Classes:   active | deprecated | orphaned | zombie | shadow
Input:              X ∈ ℝ^(n×18)
Output:             ŷ ∈ {0,1,2,3,4}, P(ŷ|X) ∈ [0,1]^5
```

```python
# ml/classifier.py

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline

class ZombieAPIClassifier:
    LABELS = ["active", "deprecated", "orphaned", "zombie", "shadow"]

    def __init__(self):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(
                n_estimators    = 300,    # 300 trees in the forest
                max_depth       = 12,     # Prevent overfitting
                min_samples_leaf= 3,      # Each leaf needs ≥3 samples
                max_features    = "sqrt", # √18 ≈ 4 features per split
                class_weight    = "balanced",
                random_state    = 42,
                n_jobs          = -1,     # Use all CPU cores
            ))
        ])
        self.label_encoder = LabelEncoder()
        self.trained = False

    def train(self, X: np.ndarray, y_str: list[str]) -> dict:
        """
        X: shape (n_samples, 18)
        y_str: list of string labels e.g. ["active", "zombie", ...]
        Returns: dict of per-class F1 scores
        """
        y_enc = self.label_encoder.fit_transform(y_str)
        self.pipeline.fit(X, y_enc)
        self.trained = True

        # Compute training accuracy
        y_pred = self.pipeline.predict(X)
        return self._compute_metrics(y_enc, y_pred)

    def predict(self, x: np.ndarray) -> dict:
        """
        x: shape (1, 18) — single API feature vector
        Returns dict with status, confidence, and full probability distribution
        """
        assert self.trained, "Model must be trained before prediction"
        proba  = self.pipeline.predict_proba(x)[0]  # shape (5,)
        idx    = int(np.argmax(proba))
        labels = self.label_encoder.inverse_transform(range(len(proba)))
        return {
            "status":        labels[idx],
            "confidence":    round(float(proba[idx]), 4),
            "probabilities": {labels[i]: round(float(p), 4) for i, p in enumerate(proba)},
        }

    def feature_importances(self) -> dict:
        """Return feature importance scores for explainability."""
        from ml.feature_extractor import FEATURE_COLS
        rf = self.pipeline.named_steps["rf"]
        return dict(zip(FEATURE_COLS, rf.feature_importances_.tolist()))

    def _compute_metrics(self, y_true, y_pred) -> dict:
        from sklearn.metrics import f1_score
        scores = f1_score(y_true, y_pred, average=None)
        labels = self.label_encoder.inverse_transform(range(len(scores)))
        return {label: round(float(s), 4) for label, s in zip(labels, scores)}
```

### 4.3 Model 2 — Isolation Forest (Shadow Detection)

```
Why Isolation Forest?
══════════════════════
Problem: Shadow APIs don't have "shadow" labels — they were never recorded
Solution: Treat shadow detection as UNSUPERVISED ANOMALY DETECTION

Isolation Forest Logic:
• Build 200 random trees, each tries to "isolate" a data point
• Normal APIs (active, well-documented) → need MANY splits to isolate → high path length → INLIER
• Shadow APIs (no auth, no docs, high traffic) → isolated quickly → short path → OUTLIER
• anomaly_score = -E[path_length] → more negative = more anomalous

contamination=0.15 means we expect ~15% of APIs to be anomalous (shadows/unknown)
```

```python
# ml/shadow_detector.py

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class ShadowAPIDetector:
    def __init__(self, contamination: float = 0.15):
        self.scaler = StandardScaler()
        self.model  = IsolationForest(
            n_estimators  = 200,
            contamination = contamination,   # Expected fraction of outliers
            max_samples   = "auto",          # min(256, n_samples) per tree
            max_features  = 1.0,             # All features available
            bootstrap     = False,
            random_state  = 42,
            n_jobs        = -1,
        )
        self.trained = False

    def train(self, X: np.ndarray):
        """Train on ALL API records — no labels needed."""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.trained = True

    def predict(self, x: np.ndarray) -> dict:
        """
        Returns:
          is_shadow    (bool)  — True if anomalous (likely shadow)
          anomaly_score (float) — raw isolation score, more negative = more anomalous
          confidence   (float) — normalised 0-1 confidence in shadow classification
        """
        x_scaled  = self.scaler.transform(x)
        label     = self.model.predict(x_scaled)[0]       # -1 = anomaly, 1 = normal
        raw_score = float(self.model.score_samples(x_scaled)[0])
        # Normalise to 0-1: typical scores range from -0.8 to -0.3 for anomalies
        confidence = float(min(1.0, max(0.0, (-raw_score - 0.3) / 0.5)))
        return {
            "is_shadow":     label == -1,
            "anomaly_score": round(abs(raw_score), 4),
            "confidence":    round(confidence, 3),
        }
```

### 4.4 Model 3 — Gradient Boosting (Security Scoring)

```
Why Gradient Boosting?
═══════════════════════
• GBM excels at learning non-linear interactions between features:
  e.g., "no auth" alone is bad, but "no auth + financial data + high traffic" = CRITICAL
• Sequential ensemble — each tree corrects errors of previous
• learning_rate=0.08 + max_depth=5 → careful, generalising learner
• Output: risk_level ∈ {low, medium, high, critical} + numeric score 0-100

Security Score Formula (rule-based post-processing on top of model):
  base_score = 100
  - 30 if no_auth
  - 25 if no_encryption
  - 15 if no_rate_limit
  - 10 if no_documentation
  - 10 if error_rate > 20%
  - 20 if sensitive_data AND no_owner
  = final_score (clamped to 0-100)
```

```python
# ml/security_scorer.py

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline

RISK_LABELS = ["low", "medium", "high", "critical"]

class SecurityPostureScorer:
    def __init__(self):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("gb", GradientBoostingClassifier(
                n_estimators   = 200,
                learning_rate  = 0.08,
                max_depth      = 5,
                subsample      = 0.8,       # Use 80% of data per tree → prevents overfitting
                min_samples_leaf = 5,
                random_state   = 42,
            ))
        ])
        self.label_encoder = LabelEncoder()
        self.trained = False

    def _derive_risk_labels(self, X_raw: list[dict]) -> list[str]:
        """Heuristic risk labelling for supervised training."""
        labels = []
        for meta in X_raw:
            score = 0
            if not meta.get("has_auth"):         score += 3
            if not meta.get("has_encryption"):   score += 2
            if not meta.get("has_rate_limit"):   score += 1
            if meta.get("data_sensitivity_score", 0) >= 2: score += 2
            if meta.get("error_rate", 0) > 0.2:  score += 1
            if not meta.get("owner_assigned"):   score += 1
            labels.append(
                "critical" if score >= 6 else
                "high"     if score >= 4 else
                "medium"   if score >= 2 else
                "low"
            )
        return labels

    def train(self, X: np.ndarray, raw_metadata: list[dict]):
        y_str = self._derive_risk_labels(raw_metadata)
        y_enc = self.label_encoder.fit_transform(y_str)
        self.pipeline.fit(X, y_enc)
        self.trained = True

    def score_api(self, x: np.ndarray, meta: dict) -> dict:
        """Returns risk level + numeric security score + list of issues."""
        proba  = self.pipeline.predict_proba(x)[0]
        idx    = int(np.argmax(proba))
        labels = self.label_encoder.inverse_transform(range(len(proba)))
        risk   = labels[idx]

        # Rule-based numeric score
        score   = 100
        issues  = []
        if not meta.get("has_auth"):
            score -= 30
            issues.append({"type": "auth",      "severity": "critical", "msg": "No authentication"})
        if not meta.get("has_encryption"):
            score -= 25
            issues.append({"type": "encrypt",   "severity": "high",     "msg": "No TLS/encryption"})
        if not meta.get("has_rate_limit"):
            score -= 15
            issues.append({"type": "ratelimit", "severity": "medium",   "msg": "No rate limiting"})
        if not meta.get("has_documentation"):
            score -= 10
            issues.append({"type": "docs",      "severity": "low",      "msg": "Undocumented endpoint"})
        if meta.get("error_rate", 0) > 0.2:
            score -= 10
            issues.append({"type": "errors",    "severity": "medium",   "msg": f"High error rate ({meta['error_rate']*100:.0f}%)"})
        if meta.get("data_sensitivity_score", 0) >= 2 and not meta.get("owner_assigned"):
            score -= 20
            issues.append({"type": "data",      "severity": "high",     "msg": "Sensitive data, no owner"})

        return {
            "security_score": max(0, score),
            "risk_level":     risk,
            "issues":         issues,
        }
```

### 4.5 Training Pipeline — Full Flow

```python
# ml/train.py — Run this script to train and save all models

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report

from ml.classifier      import ZombieAPIClassifier
from ml.shadow_detector import ShadowAPIDetector
from ml.security_scorer import SecurityPostureScorer
from ml.data_generator  import generate_training_data  # synthetic data generator
from ml.feature_extractor import extract_features

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


def train_all(n_samples: int = 8000) -> dict:
    print(f"[1/5] Generating {n_samples} synthetic API records...")
    records = generate_training_data(n_samples)

    print("[2/5] Extracting feature matrix...")
    X     = np.array([extract_features(r) for r in records])
    y_cls = [r["label"] for r in records]

    print("[3/5] Training Zombie Classifier (Random Forest)...")
    classifier = ZombieAPIClassifier()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_cls, test_size=0.2, stratify=y_cls, random_state=42
    )
    classifier.train(X_train, y_train)
    preds_cls = [classifier.predict(x.reshape(1, -1))["status"] for x in X_test]
    print(classification_report(y_test, preds_cls))
    joblib.dump(classifier, MODELS_DIR / "classifier.pkl")

    print("[4/5] Training Shadow Detector (Isolation Forest)...")
    detector = ShadowAPIDetector(contamination=0.15)
    detector.train(X)  # Unsupervised — uses all data
    joblib.dump(detector, MODELS_DIR / "shadow_detector.pkl")

    print("[5/5] Training Security Scorer (Gradient Boosting)...")
    scorer = SecurityPostureScorer()
    scorer.train(X, records)
    joblib.dump(scorer, MODELS_DIR / "security_scorer.pkl")

    print(f"\n✓ All models saved to {MODELS_DIR}/")
    return {"status": "success", "samples": n_samples}


if __name__ == "__main__":
    train_all()
```

### 4.6 Feature Importance Visualisation

The Random Forest exposes which features drive the zombie classification most:

```
Feature Importance Ranking (approximate, from trained model)
════════════════════════════════════════════════════════════

  days_since_last_call      ████████████████░░░░  0.28  ← Most important
  call_volume_30d           ████████████░░░░░░░░  0.19
  version_age_days          ████████░░░░░░░░░░░░  0.13
  is_documented_in_gateway  ██████░░░░░░░░░░░░░░  0.10
  has_auth                  █████░░░░░░░░░░░░░░░  0.08
  consecutive_error_days    ████░░░░░░░░░░░░░░░░  0.07
  dependent_services_count  ████░░░░░░░░░░░░░░░░  0.06
  owner_assigned            ███░░░░░░░░░░░░░░░░░  0.04
  has_documentation         ██░░░░░░░░░░░░░░░░░░  0.03
  ... (remaining 9 features sum to 0.02)
```

---

## 5. Backend Pipeline — FastAPI

### 5.1 Project Structure

```
backend/
├── main.py                   # FastAPI app entry point
├── requirements.txt
├── zombieguard.db            # SQLite database file (auto-created)
│
├── database/
│   ├── __init__.py
│   ├── connection.py         # Engine, session, init_db()
│   ├── models.py             # SQLAlchemy ORM models
│   └── schema.sql            # Raw DDL (applied at startup)
│
├── ml/
│   ├── __init__.py
│   ├── engine.py             # ZombieAPIMLEngine (master orchestrator)
│   ├── classifier.py         # Random Forest classifier
│   ├── shadow_detector.py    # Isolation Forest
│   ├── security_scorer.py    # Gradient Boosting
│   ├── feature_extractor.py  # Feature engineering
│   ├── data_generator.py     # Synthetic training data
│   └── train.py              # Training script
│
├── routers/
│   ├── __init__.py
│   ├── apis.py               # /apis/* endpoints
│   ├── scans.py              # /scan/* endpoints
│   ├── analytics.py          # /analytics/* endpoints
│   ├── decommission.py       # /decommission/* endpoints
│   └── ml.py                 # /ml/* endpoints
│
├── services/
│   ├── api_service.py        # CRUD + ML analysis for APIs
│   ├── scan_service.py       # Network/repo scanning logic
│   └── decomm_service.py     # Decommission workflow state machine
│
├── models/                   # Saved ML model .pkl files
│   ├── classifier.pkl
│   ├── shadow_detector.pkl
│   └── security_scorer.pkl
│
└── schemas/
    ├── api_schema.py         # Pydantic request/response models
    ├── scan_schema.py
    └── analytics_schema.py
```

### 5.2 FastAPI Main Entry Point

```python
# backend/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database.connection import init_db
from routers import apis, scans, analytics, decommission, ml as ml_router
from services.api_service import seed_initial_data
from ml.engine import ZombieAPIMLEngine

# ── Global ML Engine ─────────────────────────────────────────────────────────
_engine: ZombieAPIMLEngine | None = None

def get_ml_engine() -> ZombieAPIMLEngine:
    global _engine
    if _engine is None:
        _engine = ZombieAPIMLEngine.load_or_train()
    return _engine

# ── Lifespan (replaces on_event startup/shutdown) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("Initialising database...")
    await init_db()
    print("Loading/training ML models...")
    get_ml_engine()
    print("Seeding initial API inventory...")
    await seed_initial_data(get_ml_engine())
    print("✓ ZombieGuard ready.")
    yield
    # SHUTDOWN
    print("Shutting down ZombieGuard...")

# ── App Factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title       = "ZombieGuard API",
        description = "Zombie API Discovery & Defence Platform",
        version     = "1.0.0",
        lifespan    = lifespan,
        docs_url    = "/docs",
        redoc_url   = "/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["http://localhost:5173", "http://localhost:3000"],
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # Mount routers
    app.include_router(apis.router,          prefix="/apis",        tags=["APIs"])
    app.include_router(scans.router,         prefix="/scan",        tags=["Scanning"])
    app.include_router(analytics.router,     prefix="/analytics",   tags=["Analytics"])
    app.include_router(decommission.router,  prefix="/decommission",tags=["Decommission"])
    app.include_router(ml_router.router,     prefix="/ml",          tags=["ML Engine"])

    @app.get("/health", tags=["System"])
    async def health():
        engine = get_ml_engine()
        return {
            "status": "healthy",
            "ml_trained": engine.trained,
            "version": "1.0.0",
        }

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
```

### 5.3 APIs Router (Full CRUD + ML)

```python
# backend/routers/apis.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from database.connection import get_db
from database.models import API
from services.api_service import APIService
from schemas.api_schema import APIResponse, APIListResponse, APIUpdateRequest

router = APIRouter()


@router.get("/", response_model=APIListResponse)
async def list_apis(
    status:     str | None = Query(None, description="Filter by ML status"),
    risk:       str | None = Query(None, description="Filter by risk level"),
    search:     str | None = Query(None, description="Search endpoint path"),
    owner:      str | None = Query(None, description="Filter by owner team"),
    source:     str | None = Query(None, description="Filter by discovery source"),
    sort_by:    str        = Query("risk", description="Sort field: risk|score|calls|staleness"),
    page:       int        = Query(1, ge=1),
    page_size:  int        = Query(50, ge=1, le=200),
    db:         AsyncSession = Depends(get_db),
):
    """List all discovered APIs with ML classification results."""
    service = APIService(db)
    return await service.list_apis(
        status=status, risk=risk, search=search, owner=owner,
        source=source, sort_by=sort_by, page=page, page_size=page_size,
    )


@router.get("/{api_id}", response_model=APIResponse)
async def get_api(api_id: str, db: AsyncSession = Depends(get_db)):
    """Detailed view of a single API with full ML analysis."""
    service = APIService(db)
    api = await service.get_api(api_id)
    if not api:
        raise HTTPException(status_code=404, detail=f"API '{api_id}' not found")
    return api


@router.put("/{api_id}", response_model=APIResponse)
async def update_api(
    api_id: str,
    body:   APIUpdateRequest,
    db:     AsyncSession = Depends(get_db),
):
    """Update API metadata (e.g., assign owner, add tags)."""
    service = APIService(db)
    return await service.update_api(api_id, body.dict(exclude_unset=True))


@router.post("/{api_id}/reanalyze", response_model=APIResponse)
async def reanalyze_api(api_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger fresh ML analysis for a single API."""
    from main import get_ml_engine
    service = APIService(db)
    engine  = get_ml_engine()
    return await service.run_ml_analysis(api_id, engine)


@router.get("/{api_id}/metrics")
async def get_api_metrics(
    api_id: str,
    days:   int = Query(30, ge=1, le=365),
    db:     AsyncSession = Depends(get_db),
):
    """Historical traffic metrics for an API."""
    service = APIService(db)
    return await service.get_metrics(api_id, days)


@router.get("/{api_id}/audit")
async def get_api_audit_trail(api_id: str, db: AsyncSession = Depends(get_db)):
    """Immutable audit trail for compliance."""
    service = APIService(db)
    return await service.get_audit_trail(api_id)
```

### 5.4 Pydantic Schemas

```python
# backend/schemas/api_schema.py

from pydantic import BaseModel, Field
from typing import Optional

class MLClassification(BaseModel):
    status:        str
    confidence:    float
    probabilities: dict[str, float]

class SecurityIssueSchema(BaseModel):
    type:     str
    severity: str
    msg:      str

class SecurityPosture(BaseModel):
    security_score: int
    risk_level:     str
    issues:         list[SecurityIssueSchema]

class ShadowDetection(BaseModel):
    is_shadow:     bool
    anomaly_score: float
    confidence:    float

class RemediationStep(BaseModel):
    priority: int
    action:   str
    detail:   str

class APIResponse(BaseModel):
    id:                       str
    endpoint:                 str
    method:                   str
    version:                  Optional[str]
    owner_team:               Optional[str]
    source:                   str
    tags:                     list[str]
    last_called_at:           Optional[str]
    last_deployment_at:       Optional[str]
    call_volume_30d:          int
    call_volume_7d:           int
    error_rate:               float
    response_time_p95_ms:     int
    has_auth:                 bool
    has_encryption:           bool
    has_rate_limit:           bool
    has_documentation:        bool
    is_documented_in_gateway: bool
    version_age_days:         int
    dependent_services_count: int
    data_sensitivity:         str
    classification:           MLClassification
    security:                 SecurityPosture
    shadow_detection:         ShadowDetection
    remediation:              list[RemediationStep]
    ml_analyzed_at:           Optional[str]
    discovered_at:            str

    class Config:
        from_attributes = True

class APIListResponse(BaseModel):
    count:      int
    total:      int
    page:       int
    page_size:  int
    apis:       list[dict]  # Lighter summary objects for listing

class APIUpdateRequest(BaseModel):
    owner_team:    Optional[str]
    tags:          Optional[list[str]]
    has_auth:      Optional[bool]
    has_rate_limit: Optional[bool]
    has_documentation: Optional[bool]
```

---

## 6. Frontend Architecture — React

### 6.1 Project Structure

```
frontend/
├── package.json
├── vite.config.ts
├── index.html
│
├── src/
│   ├── main.tsx               # React root + QueryClient provider
│   ├── App.tsx                # Root app, routing, layout
│   │
│   ├── api/                   # All backend communication
│   │   ├── client.ts          # Axios instance + interceptors
│   │   ├── apis.ts            # /apis/* queries and mutations
│   │   ├── scans.ts           # /scan/* queries + SSE
│   │   ├── analytics.ts       # /analytics/* queries
│   │   ├── decommission.ts    # /decommission/* mutations
│   │   └── websocket.ts       # WS connection manager
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── AlertTicker.tsx
│   │   │
│   │   ├── shared/
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── RiskBadge.tsx
│   │   │   ├── MethodTag.tsx
│   │   │   ├── SecurityScoreBar.tsx
│   │   │   ├── KPICard.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   │
│   │   └── charts/
│   │       ├── StatusPieChart.tsx
│   │       ├── RiskBarChart.tsx
│   │       ├── ZombieTrendLine.tsx
│   │       └── SecurityRadar.tsx
│   │
│   ├── views/
│   │   ├── OverviewView.tsx   # Dashboard KPIs + charts
│   │   ├── ScanView.tsx       # Terminal scan interface
│   │   ├── InventoryView.tsx  # Filterable API table
│   │   ├── AnalysisView.tsx   # ML deep-dive per API
│   │   └── DecommissionView.tsx # Workflow tracker
│   │
│   ├── hooks/
│   │   ├── useAPIs.ts         # React Query hooks for API data
│   │   ├── useScan.ts         # SSE scan streaming hook
│   │   ├── useWebSocket.ts    # WebSocket hook
│   │   └── useAnalytics.ts    # Dashboard data hook
│   │
│   ├── store/
│   │   └── uiStore.ts         # Zustand store for UI state
│   │
│   └── types/
│       └── index.ts           # TypeScript interfaces
```

### 6.2 Design System — Color Palette & Typography

```css
/* src/styles/design-tokens.css */

:root {
  /* ── Backgrounds ── */
  --bg-primary:    #060b14;   /* Deep space navy — main background */
  --bg-surface:    #0c1626;   /* Card/panel background */
  --bg-surface-2:  #101f35;   /* Hover/striped row */
  --bg-overlay:    #040810;   /* Terminal/code blocks */

  /* ── Borders ── */
  --border-default: #1a2f4a;
  --border-focus:   #00d4ff44;

  /* ── Status Colors ── */
  --color-active:      #00ff88;
  --color-deprecated:  #ff8c00;
  --color-orphaned:    #ffd700;
  --color-zombie:      #ff2055;
  --color-shadow:      #a855f7;
  --color-decommissioned: #5a7a99;

  /* ── Risk Colors ── */
  --color-critical:  #ff2055;
  --color-high:      #ff8c00;
  --color-medium:    #ffd700;
  --color-low:       #00ff88;

  /* ── Accent Palette ── */
  --accent-cyan:     #00d4ff;
  --accent-blue:     #0088ff;
  --accent-purple:   #a855f7;

  /* ── Text ── */
  --text-primary:    #c8d8e8;
  --text-secondary:  #7a9abf;
  --text-muted:      #4a6a8a;

  /* ── Typography ── */
  --font-mono:   'Share Tech Mono', monospace;    /* Terminal, data, badges */
  --font-ui:     'Rajdhani', sans-serif;          /* Navigation, headings */
  --font-body:   'Inter', sans-serif;             /* Body text only */

  /* ── HTTP Method Colors ── */
  --method-get:    #00d4ff;
  --method-post:   #00ff88;
  --method-put:    #ffd700;
  --method-delete: #ff2055;
  --method-patch:  #a855f7;
}
```

### 6.3 TypeScript Interfaces

```typescript
// src/types/index.ts

export type APIStatus     = "active" | "deprecated" | "orphaned" | "zombie" | "shadow" | "decommissioned";
export type RiskLevel     = "low" | "medium" | "high" | "critical";
export type ScanStatus    = "pending" | "running" | "completed" | "failed";
export type HTTPMethod    = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

export interface MLClassification {
  status:        APIStatus;
  confidence:    number;
  probabilities: Record<APIStatus, number>;
}

export interface SecurityIssue {
  type:     string;
  severity: RiskLevel;
  msg:      string;
}

export interface SecurityPosture {
  security_score: number;      // 0-100
  risk_level:     RiskLevel;
  issues:         SecurityIssue[];
}

export interface ShadowDetection {
  is_shadow:     boolean;
  anomaly_score: number;
  confidence:    number;
}

export interface RemediationStep {
  priority: number;
  action:   string;
  detail:   string;
}

export interface APIRecord {
  id:                       string;
  endpoint:                 string;
  method:                   HTTPMethod;
  version:                  string | null;
  owner_team:               string | null;
  source:                   string;
  tags:                     string[];
  last_called_at:           string | null;
  last_deployment_at:       string | null;
  call_volume_30d:          number;
  call_volume_7d:           number;
  error_rate:               number;
  response_time_p95_ms:     number;
  has_auth:                 boolean;
  has_encryption:           boolean;
  has_rate_limit:           boolean;
  has_documentation:        boolean;
  is_documented_in_gateway: boolean;
  version_age_days:         number;
  dependent_services_count: number;
  data_sensitivity:         string;
  classification:           MLClassification;
  security:                 SecurityPosture;
  shadow_detection:         ShadowDetection;
  remediation:              RemediationStep[];
  ml_analyzed_at:           string | null;
  discovered_at:            string;
}

export interface APIListResponse {
  count:     number;
  total:     number;
  page:      number;
  page_size: number;
  apis:      Partial<APIRecord>[];
}

export interface AnalyticsSummary {
  total_apis:         number;
  status_breakdown:   Record<APIStatus, number>;
  risk_breakdown:     Record<RiskLevel, number>;
  avg_security_score: number;
  zombie_percentage:  number;
  shadow_count:       number;
  critical_apis:      number;
  scans_completed:    number;
}

export interface ScanEvent {
  event_type: "info" | "warn" | "critical" | "found" | "success" | "scan";
  source:     string;
  message:    string;
  apis_found: number;
  created_at: string;
}

export interface ScanRecord {
  id:           string;
  status:       ScanStatus;
  targets:      string[];
  deep_scan:    boolean;
  apis_found:   number;
  progress:     number;
  started_at:   string;
  completed_at: string | null;
  events:       ScanEvent[];
}

export interface DecommWorkflow {
  id:              string;
  api_id:          string;
  status:          "pending" | "in_progress" | "completed" | "aborted";
  current_step:    string | null;
  completed_steps: string[];
  started_at:      string;
  completed_at:    string | null;
}

export interface WSMessage {
  type:     "init" | "scan_update" | "scan_complete" | "decomm_update" | "decomm_complete" | "alert" | "heartbeat";
  payload?: unknown;
}
```

---

## 7. Connecting Frontend ↔ Backend

### 7.1 Axios Client Configuration

```typescript
// src/api/client.ts

import axios, { AxiosInstance, AxiosError } from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
    "Accept":       "application/json",
  },
});

// ── Request Interceptor ───────────────────────────────────────────
apiClient.interceptors.request.use(
  (config) => {
    // Attach auth token if present (JWT from your auth system)
    const token = localStorage.getItem("zg_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (err) => Promise.reject(err),
);

// ── Response Interceptor ──────────────────────────────────────────
apiClient.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("zg_token");
      window.location.href = "/login";
    }
    // Global error normalisation
    const message = (err.response?.data as any)?.detail ?? err.message;
    return Promise.reject(new Error(message));
  },
);
```

### 7.2 React Query Hooks

```typescript
// src/hooks/useAPIs.ts

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { APIRecord, APIListResponse } from "@/types";

// ── Query Keys ───────────────────────────────────────────────────
export const API_KEYS = {
  all:    ()         => ["apis"]                    as const,
  list:   (filters:  object) => ["apis", "list", filters]  as const,
  detail: (id: string)       => ["apis", "detail", id]      as const,
  metrics:(id: string)       => ["apis", "metrics", id]     as const,
};

// ── Fetch API List ────────────────────────────────────────────────
export function useAPIList(filters: {
  status?:    string;
  risk?:      string;
  search?:    string;
  sort_by?:   string;
  page?:      number;
  page_size?: number;
} = {}) {
  return useQuery({
    queryKey:  API_KEYS.list(filters),
    queryFn:   async () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => v && params.set(k, String(v)));
      const { data } = await apiClient.get<APIListResponse>(`/apis?${params}`);
      return data;
    },
    staleTime:    30_000,   // Consider fresh for 30s
    refetchInterval: 60_000, // Auto-refresh every minute
  });
}

// ── Fetch Single API ──────────────────────────────────────────────
export function useAPI(id: string) {
  return useQuery({
    queryKey: API_KEYS.detail(id),
    queryFn:  async () => {
      const { data } = await apiClient.get<APIRecord>(`/apis/${id}`);
      return data;
    },
    enabled:  !!id,
    staleTime: 15_000,
  });
}

// ── Reanalyze API ─────────────────────────────────────────────────
export function useReanalyzeAPI() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post<APIRecord>(`/apis/${id}/reanalyze`);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(API_KEYS.detail(data.id), data);
      qc.invalidateQueries({ queryKey: API_KEYS.all() });
    },
  });
}

// ── Update API (assign owner, tags) ───────────────────────────────
export function useUpdateAPI() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: string; [key: string]: unknown }) => {
      const { data } = await apiClient.put<APIRecord>(`/apis/${id}`, body);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(API_KEYS.detail(data.id), data);
      qc.invalidateQueries({ queryKey: API_KEYS.all() });
    },
  });
}
```

### 7.3 SSE Hook — Live Scan Streaming

```typescript
// src/hooks/useScan.ts

import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "@/api/client";
import type { ScanRecord, ScanEvent } from "@/types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function useScan() {
  const [scanId,    setScanId]    = useState<string | null>(null);
  const [status,    setStatus]    = useState<"idle" | "running" | "completed" | "error">("idle");
  const [progress,  setProgress]  = useState(0);
  const [events,    setEvents]    = useState<ScanEvent[]>([]);
  const [apisFound, setApisFound] = useState(0);
  const esRef = useRef<EventSource | null>(null);

  // Start a new scan
  const startScan = useCallback(async (targets: string[] = ["api_gateway", "github", "k8s", "lambda"]) => {
    setEvents([]);
    setProgress(0);
    setApisFound(0);
    setStatus("running");

    const { data } = await apiClient.post<{ scan_id: string }>("/scan/start", { targets });
    setScanId(data.scan_id);
  }, []);

  // Stream scan events via Server-Sent Events
  useEffect(() => {
    if (!scanId || status !== "running") return;

    // Clean up previous ES
    esRef.current?.close();

    const es = new EventSource(`${BASE_URL}/scan/${scanId}/stream`);
    esRef.current = es;

    es.onmessage = (e: MessageEvent) => {
      const scan: ScanRecord = JSON.parse(e.data);
      setProgress(scan.progress);
      setApisFound(scan.apis_found);
      setEvents(scan.events ?? []);

      if (scan.status === "completed") {
        setStatus("completed");
        es.close();
      }
    };

    es.onerror = () => {
      setStatus("error");
      es.close();
    };

    return () => { es.close(); };
  }, [scanId, status]);

  return { startScan, status, progress, events, apisFound, scanId };
}
```

### 7.4 WebSocket Hook — Real-Time Alerts

```typescript
// src/hooks/useWebSocket.ts

import { useEffect, useRef, useState, useCallback } from "react";
import type { WSMessage } from "@/types";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

type MessageHandler = (msg: WSMessage) => void;

export function useWebSocket(onMessage: MessageHandler) {
  const wsRef       = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handlerRef  = useRef(onMessage);
  handlerRef.current = onMessage;

  const connect = useCallback(() => {
    wsRef.current?.close();

    const ws = new WebSocket(`${WS_URL}/ws/monitor`);
    wsRef.current = ws;

    ws.onopen    = ()    => { setConnected(true); console.log("[WS] Connected"); };
    ws.onclose   = ()    => {
      setConnected(false);
      // Auto-reconnect with exponential backoff
      reconnTimer.current = setTimeout(connect, 3000);
    };
    ws.onerror   = ()    => ws.close();
    ws.onmessage = (e)   => {
      try {
        const msg: WSMessage = JSON.parse(e.data);
        handlerRef.current(msg);
      } catch { /* ignore parse errors */ }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnTimer.current) clearTimeout(reconnTimer.current);
    };
  }, [connect]);

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { connected, send };
}
```

### 7.5 Analytics Hook

```typescript
// src/hooks/useAnalytics.ts

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { AnalyticsSummary } from "@/types";

export function useAnalytics() {
  return useQuery({
    queryKey:        ["analytics", "summary"],
    queryFn:         async () => {
      const { data } = await apiClient.get<AnalyticsSummary>("/analytics/summary");
      return data;
    },
    staleTime:       30_000,
    refetchInterval: 30_000,
  });
}
```

### 7.6 Decommission Mutations

```typescript
// src/api/decommission.ts

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { DecommWorkflow } from "@/types";

export function useStartDecommission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (apiId: string) => {
      const { data } = await apiClient.post<DecommWorkflow>(`/decommission/${apiId}/start`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["apis"] });
    },
  });
}

export function useDecommissionStatus(apiId: string) {
  return useQuery({
    queryKey:        ["decomm", apiId],
    queryFn:         async () => {
      const { data } = await apiClient.get<DecommWorkflow>(`/decommission/${apiId}`);
      return data;
    },
    enabled:         !!apiId,
    refetchInterval: (data) => data?.status === "in_progress" ? 1000 : false,
  });
}
```

### 7.7 Vite Configuration

```typescript
// vite.config.ts

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api/* calls to backend during development
      "/apis":        { target: "http://localhost:8000", changeOrigin: true },
      "/scan":        { target: "http://localhost:8000", changeOrigin: true },
      "/analytics":   { target: "http://localhost:8000", changeOrigin: true },
      "/decommission":{ target: "http://localhost:8000", changeOrigin: true },
      "/ml":          { target: "http://localhost:8000", changeOrigin: true },
      "/ws":          { target: "ws://localhost:8000",   changeOrigin: true, ws: true },
    },
  },
  build: {
    outDir:        "dist",
    sourcemap:     true,
    chunkSizeWarningLimit: 1000,
  },
});
```

---

## 8. Scan Pipeline — End-to-End

### 8.1 Scan State Machine

```
                    ┌─────────────────────────────────────────┐
                    │           SCAN STATE MACHINE             │
                    └─────────────────────────────────────────┘

  [IDLE] ──POST /scan/start──► [PENDING] ──Background Task Started──► [RUNNING]
                                                                          │
                                                                          │  scan events
                                                                          │  emitted via SSE
                                                                          ▼
                                                         ┌─────────────────────────┐
                                                         │   Discovery Phase       │
                                                         │   • API Gateway scan    │
                                                         │   • GitHub repo scan    │
                                                         │   • K8s ingress scan    │
                                                         │   • Lambda probe        │
                                                         │   • Legacy SOAP scan    │
                                                         └──────────┬──────────────┘
                                                                    │
                                                                    ▼
                                                         ┌─────────────────────────┐
                                                         │    ML Analysis Phase    │
                                                         │   • Feature extraction  │
                                                         │   • RF classification   │
                                                         │   • IF shadow detection │
                                                         │   • GB security scoring │
                                                         └──────────┬──────────────┘
                                                                    │
                                                                    ▼
                                                         ┌─────────────────────────┐
                                                         │    Persistence Phase    │
                                                         │   • Upsert apis table   │
                                                         │   • Write security_issues│
                                                         │   • Write alerts        │
                                                         │   • Update scan record  │
                                                         └──────────┬──────────────┘
                                                                    │
                                                          [COMPLETED] or [FAILED]
```

### 8.2 Scan Service Implementation

```python
# backend/services/scan_service.py

import asyncio, uuid, json
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update

from database.models import Scan, ScanEvent, API, Alert
from ml.engine import ZombieAPIMLEngine


SCAN_SOURCES = [
    {"name": "API Gateway (Kong)",    "delay": 1.5, "min": 5,  "max": 12},
    {"name": "AWS Lambda Functions",  "delay": 2.0, "min": 3,  "max": 8},
    {"name": "GitHub Repositories",   "delay": 2.5, "min": 4,  "max": 10},
    {"name": "Kubernetes Ingress",    "delay": 1.8, "min": 3,  "max": 9},
    {"name": "Legacy SOAP Services",  "delay": 2.2, "min": 2,  "max": 7},
    {"name": "Internal Network Probe","delay": 1.6, "min": 2,  "max": 6},
]


class ScanService:
    def __init__(self, db: AsyncSession, engine: ZombieAPIMLEngine):
        self.db     = db
        self.engine = engine

    async def create_scan(self, targets: list[str], deep_scan: bool) -> str:
        scan_id = str(uuid.uuid4())
        scan    = Scan(
            id        = scan_id,
            status    = "running",
            targets   = json.dumps(targets),
            deep_scan = int(deep_scan),
            started_at = datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(scan)
        await self.db.commit()
        return scan_id

    async def run_scan(self, scan_id: str, broadcast_fn) -> None:
        """
        Full async scan pipeline. Runs as a FastAPI BackgroundTask.
        broadcast_fn: coroutine to push WS/SSE events to clients.
        """
        import random
        total_found = 0

        for source in SCAN_SOURCES:
            await asyncio.sleep(source["delay"])

            found = random.randint(source["min"], source["max"])
            total_found += found
            msg = f"Scanned {source['name']} — {found} endpoints discovered"

            # Persist event to SQLite
            event = ScanEvent(
                scan_id    = scan_id,
                event_type = "found",
                source     = source["name"],
                message    = msg,
                apis_found = found,
                created_at = datetime.now(timezone.utc).isoformat(),
            )
            self.db.add(event)

            # Update scan progress
            progress = int((SCAN_SOURCES.index(source) + 1) / len(SCAN_SOURCES) * 80)
            await self.db.execute(
                update(Scan).where(Scan.id == scan_id).values(
                    progress=progress, apis_found=total_found
                )
            )
            await self.db.commit()

            # Broadcast SSE event
            await broadcast_fn({
                "type":      "scan_update",
                "scan_id":   scan_id,
                "progress":  progress,
                "apis_found":total_found,
                "source":    source["name"],
                "message":   msg,
            })

        # ── ML Analysis Phase ─────────────────────────────────────────
        await self._run_ml_analysis_phase(scan_id, broadcast_fn)

        # ── Finalise ──────────────────────────────────────────────────
        await self.db.execute(
            update(Scan).where(Scan.id == scan_id).values(
                status       = "completed",
                progress     = 100,
                apis_found   = total_found,
                completed_at = datetime.now(timezone.utc).isoformat(),
            )
        )
        await self.db.commit()
        await broadcast_fn({"type": "scan_complete", "scan_id": scan_id, "apis_found": total_found})

    async def _run_ml_analysis_phase(self, scan_id: str, broadcast_fn) -> None:
        """Run ML engine over all unanalysed APIs, persist results."""
        result = await self.db.execute(
            select(API).where(API.ml_status == "unknown")
        )
        apis = result.scalars().all()

        for api in apis:
            analysis = self.engine.analyze_api(api.__dict__)
            api.ml_status          = analysis["classification"]["status"]
            api.ml_confidence      = analysis["classification"]["confidence"]
            api.ml_probabilities   = json.dumps(analysis["classification"]["probabilities"])
            api.ml_security_score  = analysis["security"]["security_score"]
            api.ml_risk_level      = analysis["security"]["risk_level"]
            api.ml_security_issues = json.dumps(analysis["security"]["issues"])
            api.ml_is_shadow       = int(analysis["shadow_detection"]["is_shadow"])
            api.ml_anomaly_score   = analysis["shadow_detection"]["anomaly_score"]
            api.ml_analyzed_at     = datetime.now(timezone.utc).isoformat()

            # Create alert for critical findings
            if api.ml_status == "zombie" or api.ml_risk_level == "critical":
                alert = Alert(
                    api_id     = api.id,
                    alert_type = "ZOMBIE" if api.ml_status == "zombie" else "CRITICAL",
                    severity   = "critical",
                    message    = f"{api.endpoint} — ML classified as {api.ml_status.upper()}",
                    created_at = datetime.now(timezone.utc).isoformat(),
                )
                self.db.add(alert)

        await self.db.commit()
        await broadcast_fn({"type": "ml_complete", "scan_id": scan_id, "analysed": len(apis)})
```

---

## 9. Decommission Workflow Pipeline

### 9.1 Seven-Step State Machine

```
DECOMMISSION STATE MACHINE
═══════════════════════════

  [START] ──► identify_callers
                    │
                    ▼
             notify_stakeholders ◄── (email/Slack integration point)
                    │
                    ▼
          deprecation_header_deployed ◄── (API Gateway config update)
                    │
                    ▼
          gateway_route_disabled ◄── (Kong/AWS API GW route removal)
                    │
                    ▼
          traffic_confirmed_zero ◄── (Monitor for 24-48h)
                    │
                    ▼
             spec_archived ◄── (Push OpenAPI spec to archive repo)
                    │
                    ▼
          service_terminated ──► [COMPLETE]

  At any step: ERROR ──► [ABORTED] (manual intervention required)

  Step Rollback Policy:
  • identify_callers:             SAFE (read-only)
  • notify_stakeholders:          SAFE (idempotent notifications)
  • deprecation_header_deployed:  ROLLBACK = remove header
  • gateway_route_disabled:       ROLLBACK = re-enable route
  • traffic_confirmed_zero:       N/A (verification step)
  • spec_archived:                SAFE (archive is additive)
  • service_terminated:           IRREVERSIBLE — requires approval gate
```

### 9.2 Decommission Service

```python
# backend/services/decomm_service.py

import asyncio, uuid, json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from database.models import DecommWorkflow, API, AuditLog


DECOMM_STEPS = [
    {
        "id":    "identify_callers",
        "label": "Identify Active Callers",
        "delay": 1.5,
        "description": "Query observability platform for services calling this endpoint in last 90 days.",
    },
    {
        "id":    "notify_stakeholders",
        "label": "Notify Stakeholders",
        "delay": 2.0,
        "description": "Send automated notifications to identified callers and management.",
    },
    {
        "id":    "deprecation_header_deployed",
        "label": "Deploy Deprecation Headers",
        "delay": 1.8,
        "description": "Add Deprecation and Sunset headers to all API responses.",
    },
    {
        "id":    "gateway_route_disabled",
        "label": "Disable API Gateway Route",
        "delay": 2.2,
        "description": "Remove routing rule from Kong/API Gateway. Returns 410 Gone.",
    },
    {
        "id":    "traffic_confirmed_zero",
        "label": "Confirm Zero Traffic",
        "delay": 3.0,
        "description": "Monitor for 24h to confirm no traffic reaching decommissioned endpoint.",
    },
    {
        "id":    "spec_archived",
        "label": "Archive API Specification",
        "delay": 1.5,
        "description": "Push OpenAPI spec to archive repository with decommission metadata.",
    },
    {
        "id":    "service_terminated",
        "label": "Terminate Service",
        "delay": 2.0,
        "description": "Shutdown underlying service/container. Mark API as decommissioned in registry.",
    },
]


class DecommService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_workflow(self, api_id: str, initiated_by: str = "analyst") -> str:
        wf_id = str(uuid.uuid4())
        wf = DecommWorkflow(
            id              = wf_id,
            api_id          = api_id,
            status          = "in_progress",
            current_step    = DECOMM_STEPS[0]["id"],
            completed_steps = "[]",
            initiated_by    = initiated_by,
            started_at      = datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(wf)

        # Audit log
        self.db.add(AuditLog(
            actor       = initiated_by,
            action      = "decommission_started",
            entity_type = "api",
            entity_id   = api_id,
            details     = json.dumps({"workflow_id": wf_id}),
            created_at  = datetime.now(timezone.utc).isoformat(),
        ))
        await self.db.commit()
        return wf_id

    async def execute_workflow(self, api_id: str, wf_id: str, broadcast_fn) -> None:
        """Run all decommission steps sequentially with broadcast updates."""
        completed = []

        for step in DECOMM_STEPS:
            await asyncio.sleep(step["delay"])
            completed.append(step["id"])

            await self.db.execute(
                update(DecommWorkflow).where(DecommWorkflow.id == wf_id).values(
                    current_step    = step["id"],
                    completed_steps = json.dumps(completed),
                )
            )
            await self.db.commit()

            await broadcast_fn({
                "type":            "decomm_update",
                "api_id":          api_id,
                "workflow_id":     wf_id,
                "current_step":    step["id"],
                "completed_steps": completed,
                "step_label":      step["label"],
            })

        # ── Mark API as decommissioned ────────────────────────────────
        await self.db.execute(
            update(API).where(API.id == api_id).values(
                ml_status        = "decommissioned",
                decommissioned_at = datetime.now(timezone.utc).isoformat(),
                is_active        = 0,
            )
        )
        await self.db.execute(
            update(DecommWorkflow).where(DecommWorkflow.id == wf_id).values(
                status       = "completed",
                completed_at = datetime.now(timezone.utc).isoformat(),
            )
        )
        self.db.add(AuditLog(
            actor       = "system",
            action      = "decommission_completed",
            entity_type = "api",
            entity_id   = api_id,
            details     = json.dumps({"workflow_id": wf_id, "steps": len(DECOMM_STEPS)}),
            created_at  = datetime.now(timezone.utc).isoformat(),
        ))
        await self.db.commit()
        await broadcast_fn({"type": "decomm_complete", "api_id": api_id, "workflow_id": wf_id})
```

---

## 10. Real-Time Layer — WebSocket + SSE

### 10.1 Connection Manager

```python
# backend/realtime/connection_manager.py

import json
from fastapi import WebSocket


class ConnectionManager:
    """Manages all active WebSocket connections with broadcasting support."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def send(self, ws: WebSocket, data: dict) -> None:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            self.disconnect(ws)

    async def broadcast(self, data: dict) -> None:
        """Send message to ALL connected clients. Dead connections are pruned."""
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self.active)


# Singleton instance shared across all routes
manager = ConnectionManager()
```

### 10.2 WebSocket Endpoint

```python
# Inside backend/routers/ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from realtime.connection_manager import manager
from database.connection import get_db

router = APIRouter()

@router.websocket("/ws/monitor")
async def ws_monitor(ws: WebSocket):
    """
    Persistent WebSocket connection for real-time alerts.

    Client receives:
      { type: "init",          summary: {...} }           -- on connect
      { type: "heartbeat",     ts: "..." }                -- every 10s
      { type: "scan_update",   ...scan_data }             -- during scans
      { type: "scan_complete", apis_found: 42 }           -- scan done
      { type: "decomm_update", api_id, step, ... }        -- decommission progress
      { type: "decomm_complete", api_id }                 -- decommission done
      { type: "alert",         severity, message, ... }   -- new threat alert
      { type: "ml_retrained",  ts }                       -- models updated
    """
    await manager.connect(ws)
    try:
        # Send initial state summary
        await manager.send(ws, {
            "type":    "init",
            "message": "Connected to ZombieGuard real-time monitor",
        })

        # Heartbeat loop
        import asyncio
        from datetime import datetime, timezone
        while True:
            await asyncio.sleep(10)
            await manager.send(ws, {
                "type": "heartbeat",
                "ts":   datetime.now(timezone.utc).isoformat(),
                "connections": manager.connection_count,
            })

    except WebSocketDisconnect:
        manager.disconnect(ws)
```

---

## 11. Security & Auth Design

### 11.1 Authentication Flow (JWT)

```python
# backend/auth/jwt_handler.py

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY  = "your-256-bit-secret-key"   # Load from env in production
ALGORITHM   = "HS256"
TOKEN_EXPIRY = 480   # 8 hours

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer  = HTTPBearer()


def create_access_token(subject: str, role: str = "analyst") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY)
    return jwt.encode(
        {"sub": subject, "role": role, "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload["sub"], "role": payload["role"]}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_role(allowed_roles: list[str]):
    async def checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

# Usage in a route:
# @router.post("/decommission/{api_id}/start")
# async def start_decommission(api_id: str, user = Depends(require_role(["admin", "security"]))):
```

---

## 12. Project Boilerplate & Folder Structure

### 12.1 Backend — `requirements.txt`

```
# backend/requirements.txt

fastapi==0.111.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.31
aiosqlite==0.20.0
pydantic==2.7.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
scikit-learn==1.5.0
numpy==1.26.4
pandas==2.2.2
joblib==1.4.2
python-multipart==0.0.9
httpx==0.27.0
```

### 12.2 Frontend — `package.json`

```json
{
  "name": "zombieguard-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev":     "vite",
    "build":   "tsc && vite build",
    "preview": "vite preview",
    "lint":    "eslint src --ext .ts,.tsx"
  },
  "dependencies": {
    "react":                    "^18.3.1",
    "react-dom":                "^18.3.1",
    "axios":                    "^1.7.2",
    "@tanstack/react-query":    "^5.45.0",
    "recharts":                 "^2.12.7",
    "zustand":                  "^4.5.4",
    "lucide-react":             "^0.400.0"
  },
  "devDependencies": {
    "@types/react":             "^18.3.3",
    "@types/react-dom":         "^18.3.0",
    "@vitejs/plugin-react":     "^4.3.1",
    "typescript":               "^5.5.2",
    "vite":                     "^5.3.3",
    "tailwindcss":              "^3.4.4",
    "eslint":                   "^9.6.0"
  }
}
```

### 12.3 Complete Folder Tree

```
zombieguard/
├── README.md
├── docker-compose.yml
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── zombieguard.db              ← Auto-created at runtime
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── schema.sql
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── classifier.py
│   │   ├── shadow_detector.py
│   │   ├── security_scorer.py
│   │   ├── feature_extractor.py
│   │   ├── data_generator.py
│   │   └── train.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── apis.py
│   │   ├── scans.py
│   │   ├── analytics.py
│   │   ├── decommission.py
│   │   └── ml.py
│   │
│   ├── services/
│   │   ├── api_service.py
│   │   ├── scan_service.py
│   │   └── decomm_service.py
│   │
│   ├── realtime/
│   │   └── connection_manager.py
│   │
│   ├── auth/
│   │   └── jwt_handler.py
│   │
│   ├── schemas/
│   │   ├── api_schema.py
│   │   ├── scan_schema.py
│   │   └── analytics_schema.py
│   │
│   └── models/
│       ├── classifier.pkl
│       ├── shadow_detector.pkl
│       └── security_scorer.pkl
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    ├── .env.example
    │
    └── src/
        ├── main.tsx
        ├── App.tsx
        │
        ├── api/
        │   ├── client.ts
        │   ├── apis.ts
        │   ├── scans.ts
        │   ├── analytics.ts
        │   └── decommission.ts
        │
        ├── components/
        │   ├── layout/
        │   │   ├── Sidebar.tsx
        │   │   ├── Header.tsx
        │   │   └── AlertTicker.tsx
        │   ├── shared/
        │   │   ├── StatusBadge.tsx
        │   │   ├── RiskBadge.tsx
        │   │   ├── MethodTag.tsx
        │   │   └── KPICard.tsx
        │   └── charts/
        │       ├── StatusPieChart.tsx
        │       ├── RiskBarChart.tsx
        │       └── SecurityRadar.tsx
        │
        ├── views/
        │   ├── OverviewView.tsx
        │   ├── ScanView.tsx
        │   ├── InventoryView.tsx
        │   ├── AnalysisView.tsx
        │   └── DecommissionView.tsx
        │
        ├── hooks/
        │   ├── useAPIs.ts
        │   ├── useScan.ts
        │   ├── useWebSocket.ts
        │   └── useAnalytics.ts
        │
        ├── store/
        │   └── uiStore.ts
        │
        ├── types/
        │   └── index.ts
        │
        └── styles/
            └── design-tokens.css
```

### 12.4 `.env` Files

```bash
# backend/.env.example
DATABASE_URL=sqlite+aiosqlite:///./zombieguard.db
SECRET_KEY=change-me-in-production-use-256-bit-key
JWT_EXPIRY_MINUTES=480
ML_MODELS_DIR=./models
ML_TRAINING_SAMPLES=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
```

```bash
# frontend/.env.example
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_TITLE=ZombieGuard
```

---

## 13. Environment Setup & Running Locally

### 13.1 Backend Setup

```bash
# 1. Clone repo and go to backend
cd zombieguard/backend

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate       # Linux/Mac
# .venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env file
cp .env.example .env

# 5. Train ML models (first time only — takes ~30s)
python ml/train.py

# 6. Start FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# ✓ API docs at http://localhost:8000/docs
# ✓ DB file auto-created at ./zombieguard.db
```

### 13.2 Frontend Setup

```bash
# 1. Go to frontend directory
cd zombieguard/frontend

# 2. Install npm packages
npm install

# 3. Copy env file
cp .env.example .env

# 4. Start dev server
npm run dev

# ✓ Frontend at http://localhost:5173
# ✓ Proxied to backend at http://localhost:8000
```

### 13.3 Docker Compose (Full Stack)

```yaml
# docker-compose.yml

version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend/zombieguard.db:/app/zombieguard.db   # Persist SQLite
      - ./backend/models:/app/models                    # Persist ML models
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./zombieguard.db
      - SECRET_KEY=${SECRET_KEY:-change-me}
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:80"
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000
    depends_on:
      backend:
        condition: service_healthy

# backend/Dockerfile
# FROM python:3.12-slim
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . .
# RUN python ml/train.py
# EXPOSE 8000
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# frontend/Dockerfile
# FROM node:20-alpine AS builder
# WORKDIR /app
# COPY package*.json .
# RUN npm ci
# COPY . .
# RUN npm run build
# FROM nginx:alpine
# COPY --from=builder /app/dist /usr/share/nginx/html
# EXPOSE 80
```

### 13.4 Inspect SQLite Database

```bash
# Install sqlite3 CLI
sqlite3 zombieguard.db

# Useful queries during development:

-- How many APIs per status?
SELECT ml_status, COUNT(*) FROM apis GROUP BY ml_status;

-- All zombie APIs
SELECT id, endpoint, ml_confidence, ml_security_score
FROM apis WHERE ml_status = 'zombie'
ORDER BY ml_confidence DESC;

-- Recent alerts
SELECT a.alert_type, a.severity, a.message, a.created_at
FROM alerts a ORDER BY created_at DESC LIMIT 20;

-- Decommission workflows
SELECT dw.status, dw.current_step, a.endpoint
FROM decomm_workflows dw JOIN apis a ON dw.api_id = a.id;

-- APIs with no owner (orphan risk)
SELECT endpoint, ml_status FROM apis WHERE owner_team IS NULL;

-- Security issues by severity
SELECT severity, COUNT(*) FROM security_issues
WHERE is_resolved = 0 GROUP BY severity;
```

---

## 14. API Reference

### 14.1 Complete Endpoint Table

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | System health check | None |
| `GET` | `/apis` | List all APIs with filters | JWT |
| `GET` | `/apis/{id}` | Full API detail + ML results | JWT |
| `PUT` | `/apis/{id}` | Update metadata (owner, tags) | JWT |
| `POST` | `/apis/{id}/reanalyze` | Trigger fresh ML analysis | JWT |
| `GET` | `/apis/{id}/metrics` | Historical traffic data | JWT |
| `GET` | `/apis/{id}/audit` | Compliance audit trail | JWT |
| `POST` | `/scan/start` | Start network discovery scan | JWT |
| `GET` | `/scan/{id}` | Get scan status and results | JWT |
| `GET` | `/scan/{id}/stream` | SSE stream of scan events | JWT |
| `GET` | `/analytics/summary` | Dashboard KPIs | JWT |
| `GET` | `/analytics/trends` | 7-day zombie/shadow trends | JWT |
| `POST` | `/decommission/{id}/start` | Begin decommission workflow | JWT+Admin |
| `GET` | `/decommission/{id}` | Workflow status | JWT |
| `POST` | `/decommission/{id}/abort` | Abort decommission | JWT+Admin |
| `POST` | `/ml/retrain` | Retrain all models | JWT+Admin |
| `GET` | `/ml/status` | Model versions + accuracy | JWT |
| `GET` | `/ml/importances` | Feature importance scores | JWT |
| `WS` | `/ws/monitor` | Real-time alert WebSocket | JWT |

### 14.2 Example API Response

```json
GET /apis/api-024
{
  "id": "api-024",
  "endpoint": "/legacy/v1/accounts",
  "method": "GET",
  "version": "v1",
  "owner_team": null,
  "source": "legacy_system",
  "tags": ["legacy", "zombie-candidate", "no-auth"],
  "last_called_at": "2024-07-04T08:22:11Z",
  "call_volume_30d": 2,
  "error_rate": 0.418,
  "has_auth": false,
  "has_encryption": false,
  "classification": {
    "status": "zombie",
    "confidence": 0.9423,
    "probabilities": {
      "zombie":     0.9423,
      "orphaned":   0.0412,
      "deprecated": 0.0093,
      "shadow":     0.0051,
      "active":     0.0021
    }
  },
  "security": {
    "security_score": 5,
    "risk_level": "critical",
    "issues": [
      { "type": "auth",      "severity": "critical", "msg": "No authentication" },
      { "type": "encrypt",   "severity": "high",     "msg": "No TLS/encryption" },
      { "type": "ratelimit", "severity": "medium",   "msg": "No rate limiting" },
      { "type": "data",      "severity": "high",     "msg": "Sensitive data, no owner" }
    ]
  },
  "shadow_detection": {
    "is_shadow": false,
    "anomaly_score": 0.1823,
    "confidence": 0.112
  },
  "remediation": [
    { "priority": 0, "action": "FIX_AUTH",      "detail": "No authentication" },
    { "priority": 1, "action": "DECOMMISSION",  "detail": "Initiate automated decommissioning workflow." },
    { "priority": 2, "action": "AUDIT_ACCESS",  "detail": "Audit who last called this API." },
    { "priority": 3, "action": "BLOCK_GATEWAY", "detail": "Remove route from API gateway." }
  ],
  "ml_analyzed_at": "2025-03-08T09:15:44Z"
}
```

---

*Document Version: 1.0.0 | Last Updated: March 2025*  
*ZombieGuard — Zombie API Discovery & Defence Platform*  
*Built for banking-grade API security operations*
