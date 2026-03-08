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
    unique_callers_30d       = Column(Integer, default=0)
    consecutive_error_days   = Column(Integer, default=0)
    has_auth                 = Column(Integer, default=0)
    has_encryption           = Column(Integer, default=1)
    has_rate_limit           = Column(Integer, default=0)
    has_documentation        = Column(Integer, default=0)
    is_documented_in_gateway = Column(Integer, default=0)
    version_age_days         = Column(Integer, default=0)
    dependent_services_count = Column(Integer, default=0)
    response_time_trend      = Column(Integer, default=0)
    data_sensitivity         = Column(Text, default="low")
    ml_status                = Column(Text, default="unknown")
    ml_confidence            = Column(Real, default=0.0)
    ml_probabilities         = Column(Text, default="{}")
    ml_security_score        = Column(Integer, default=0)
    ml_risk_level            = Column(Text, default="unknown")
    ml_security_issues       = Column(Text, default="[]")
    ml_is_shadow             = Column(Integer, default=0)
    ml_anomaly_score         = Column(Real, default=0.0)
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
