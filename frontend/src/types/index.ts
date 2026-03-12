export interface MLClassification {
    status: "active" | "deprecated" | "orphaned" | "zombie" | "shadow" | "unknown" | "decommissioned";
    confidence: number;
    probabilities: Record<string, number>;
}
  
export interface SecurityIssue {
    type: string;
    severity: "low" | "medium" | "high" | "critical";
    msg: string;
}

export interface SecurityPosture {
    security_score: number;
    risk_level: "low" | "medium" | "high" | "critical" | "unknown";
    issues: SecurityIssue[];
}

export interface ShadowDetection {
    is_shadow: boolean;
    anomaly_score: number;
    confidence: number;
}

export interface RemediationStep {
    priority: number;
    action: string;
    detail: string;
}

export interface APIRecord {
    id: string;
    endpoint: string;
    method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
    version?: string;
    owner_team?: string;
    source: string;
    tags: string[];
    last_called_at?: string;
    last_deployment_at?: string;
    call_volume_30d: number;
    call_volume_7d: number;
    error_rate: number;
    response_time_p95_ms: number;
    has_auth: boolean;
    has_encryption: boolean;
    has_rate_limit: boolean;
    has_documentation: boolean;
    is_documented_in_gateway: boolean;
    version_age_days: number;
    dependent_services_count: number;
    data_sensitivity: "low" | "medium" | "high" | "financial" | "pii";
    classification: MLClassification;
    security: SecurityPosture;
    shadow_detection: ShadowDetection;
    remediation: RemediationStep[];
    ml_analyzed_at?: string;
    discovered_at: string;
}

export interface APIListResponse {
    count: number;
    total: number;
    page: number;
    page_size: number;
    apis: Array<{
        id: string;
        endpoint: string;
        method: string;
        owner_team?: string;
        source: string;
        ml_status: string;
        ml_risk_level: string;
        ml_security_score: number;
        call_volume_30d: number;
        tags: string[];
        is_active: number;
    }>;
}

export interface ScanEvent {
    event_type: string;
    source?: string;
    message: string;
    apis_found: number;
    created_at: string;
}

export interface ScanRecord {
    id: string;
    status: "running" | "completed" | "error";
    targets: string[];
    progress: number;
    apis_found: number;
    started_at: string;
    completed_at?: string;
    events: ScanEvent[];
}

export interface WSMessage {
    type: string;
    [key: string]: unknown;
}

export interface AnalyticsSummary {
    total_apis: number;
    status_breakdown: Record<string, number>;
    risk_breakdown: Record<string, number>;
    avg_security_score: number;
    zombie_percentage: number;
    shadow_count: number;
    critical_apis: number;
    scans_completed: number;
}
