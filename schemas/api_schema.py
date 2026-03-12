from pydantic import BaseModel
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
    version:                  Optional[str] = None
    owner_team:               Optional[str] = None
    source:                   str
    tags:                     list[str] = []
    last_called_at:           Optional[str] = None
    last_deployment_at:       Optional[str] = None
    call_volume_30d:          int = 0
    call_volume_7d:           int = 0
    error_rate:               float = 0.0
    response_time_p95_ms:     int = 0
    has_auth:                 bool = False
    has_encryption:           bool = True
    has_rate_limit:           bool = False
    has_documentation:        bool = False
    is_documented_in_gateway: bool = False
    version_age_days:         int = 0
    dependent_services_count: int = 0
    data_sensitivity:         str = "low"
    classification:           MLClassification
    security:                 SecurityPosture
    shadow_detection:         ShadowDetection
    remediation:              list[RemediationStep] = []
    ml_analyzed_at:           Optional[str] = None
    discovered_at:            str

    class Config:
        from_attributes = True

class APIListResponse(BaseModel):
    count:      int
    total:      int
    page:       int
    page_size:  int
    apis:       list[dict]

class APIUpdateRequest(BaseModel):
    owner_team:        Optional[str] = None
    tags:              Optional[list[str]] = None
    has_auth:          Optional[bool] = None
    has_rate_limit:    Optional[bool] = None
    has_documentation: Optional[bool] = None
