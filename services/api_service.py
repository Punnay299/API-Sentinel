import json
from datetime import datetime, timezone
import random
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database.models import API, APIMetric, AuditLog
from ml.engine import ZombieAPIMLEngine
from schemas.api_schema import APIListResponse, APIResponse

class APIService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_apis(
        self,
        status: Optional[str] = None,
        risk: Optional[str] = None,
        search: Optional[str] = None,
        owner: Optional[str] = None,
        source: Optional[str] = None,
        sort_by: str = "risk",
        page: int = 1,
        page_size: int = 50,
    ) -> APIListResponse:
        query = select(API)

        if status:
            query = query.where(API.ml_status == status)
        if risk:
            query = query.where(API.ml_risk_level == risk)
        if search:
            query = query.where(API.endpoint.ilike(f"%{search}%"))
        if owner:
            if owner == "null":
                query = query.where(API.owner_team.is_(None))
            else:
                query = query.where(API.owner_team == owner)
        if source:
            query = query.where(API.source == source)

        if sort_by == "risk":
            # Rough sort by string risk isn't perfect, numeric score is better
            query = query.order_by(desc(API.ml_security_score))
        elif sort_by == "score":
            query = query.order_by(API.ml_security_score)
        elif sort_by == "calls":
            query = query.order_by(desc(API.call_volume_30d))
        elif sort_by == "staleness":
             query = query.order_by(API.last_called_at.nulls_last())

        # Count total before pagination
        total_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(total_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        apis = result.scalars().all()

        # Build list response
        api_list = []
        for api in apis:
            api_dict = {
                "id": api.id,
                "endpoint": api.endpoint,
                "method": api.method,
                "owner_team": api.owner_team,
                "source": api.source,
                "ml_status": api.ml_status,
                "ml_risk_level": api.ml_risk_level,
                "ml_security_score": api.ml_security_score,
                "call_volume_30d": api.call_volume_30d,
                "tags": json.loads(api.tags) if api.tags else [],
                "is_active": api.is_active,
            }
            api_list.append(api_dict)

        return APIListResponse(
            count=len(api_list),
            total=total,
            page=page,
            page_size=page_size,
            apis=api_list,
        )

    async def get_api(self, api_id: str) -> Optional[dict]:
        result = await self.db.execute(select(API).where(API.id == api_id))
        api = result.scalar_one_or_none()
        if not api:
            return None

        api_dict = api.__dict__.copy()
        api_dict.pop('_sa_instance_state', None)
        
        # Parse JSON fields to objects
        api_dict["tags"] = json.loads(api.tags) if api.tags else []
        
        probabilities = json.loads(api.ml_probabilities) if api.ml_probabilities else {}
        api_dict["classification"] = {
            "status": api.ml_status,
            "confidence": api.ml_confidence,
            "probabilities": probabilities,
        }
        
        issues = json.loads(api.ml_security_issues) if api.ml_security_issues else []
        api_dict["security"] = {
            "security_score": api.ml_security_score,
            "risk_level": api.ml_risk_level,
            "issues": issues,
        }
        
        api_dict["shadow_detection"] = {
            "is_shadow": bool(api.ml_is_shadow),
            "anomaly_score": api.ml_anomaly_score,
            "confidence": api.ml_confidence, # In design it uses confidence
        }

        # Simulated remediation steps for now based on risk level
        remediation = []
        if api.ml_risk_level == "critical":
            remediation.append({"priority": 1, "action": "DECOMMISSION", "detail": "Initiate automated decommissioning workflow immediately."})
        elif api.ml_status == "zombie":
             remediation.append({"priority": 1, "action": "DECOMMISSION", "detail": "API is a zombie. Decommission."})
        elif not api.has_auth:
             remediation.append({"priority": 1, "action": "FIX_AUTH", "detail": "No authentication detected."})

        api_dict["remediation"] = remediation

        return api_dict

    async def update_api(self, api_id: str, updates: dict) -> Optional[dict]:
        result = await self.db.execute(select(API).where(API.id == api_id))
        api = result.scalar_one_or_none()
        if not api:
            return None

        # Apply updates
        if "owner_team" in updates:
            api.owner_team = updates["owner_team"]
        if "tags" in updates:
            api.tags = json.dumps(updates["tags"])
        if "has_auth" in updates:
            api.has_auth = int(updates["has_auth"])
        if "has_rate_limit" in updates:
            api.has_rate_limit = int(updates["has_rate_limit"])
        if "has_documentation" in updates:
            api.has_documentation = int(updates["has_documentation"])

        api.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Log action
        audit_log = AuditLog(
            action="api_updated",
            entity_type="api",
            entity_id=api_id,
            details=json.dumps(updates),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        self.db.add(audit_log)

        await self.db.commit()
        return await self.get_api(api_id)

    async def run_ml_analysis(self, api_id: str, engine: ZombieAPIMLEngine) -> Optional[dict]:
        result = await self.db.execute(select(API).where(API.id == api_id))
        api = result.scalar_one_or_none()
        if not api:
            return None

        api_dict = api.__dict__.copy()
        api_dict.pop('_sa_instance_state', None)

        analysis = await engine.analyze_api(api_dict)

        api.ml_status = analysis["classification"]["status"]
        api.ml_confidence = float(analysis["classification"]["confidence"])
        api.ml_probabilities = json.dumps(analysis["classification"]["probabilities"])
        api.ml_security_score = analysis["security"]["security_score"]
        api.ml_risk_level = analysis["security"]["risk_level"]
        api.ml_security_issues = json.dumps(analysis["security"]["issues"])
        api.ml_is_shadow = int(analysis["shadow_detection"]["is_shadow"])
        api.ml_anomaly_score = float(analysis["shadow_detection"]["anomaly_score"])
        api.ml_analyzed_at = datetime.now(timezone.utc).isoformat()

        audit_log = AuditLog(
            action="ml_analysis_triggered",
            entity_type="api",
            entity_id=api_id,
            details=json.dumps({"status": api.ml_status, "risk": api.ml_risk_level}),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        self.db.add(audit_log)

        await self.db.commit()
        return await self.get_api(api_id)

    async def get_metrics(self, api_id: str, days: int = 30) -> list[dict]:
        # Return mock metrics for now, as simulating 30 days of data point by point involves a lot of DB rows
        # In a real app we'd query API_Metric
        metrics = []
        base_calls = random.randint(10, 1000)
        for i in range(days, -1, -1):
            date_str = (datetime.now(timezone.utc).replace(second=0, microsecond=0) - __import__('datetime').timedelta(days=i)).isoformat()
            metrics.append({
                "recorded_at": date_str,
                "call_count": base_calls + random.randint(-int(base_calls * 0.1), int(base_calls * 0.1)),
                "error_count": random.randint(0, int(base_calls * 0.05)),
                "p95_latency_ms": random.randint(50, 500),
                "unique_callers": random.randint(1, 20)
            })
        return metrics

    async def get_audit_trail(self, api_id: str) -> list[dict]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.entity_id == api_id)
            .order_by(AuditLog.created_at.desc())
        )
        logs = result.scalars().all()
        return [
            {
                "id": log.id,
                "actor": log.actor,
                "action": log.action,
                "details": json.loads(log.details) if log.details else {},
                "created_at": log.created_at
            }
            for log in logs
        ]

async def seed_initial_data(engine: ZombieAPIMLEngine, db: AsyncSession):
    # Check if DB has any APIs
    count = await db.scalar(select(func.count(API.id)))
    if count > 0:
        print(f"Database already seeded. {count} APIs found.")
        return

    print("Seeding database from api_inventory.json...")
    try:
        with open("api_inventory.json", "r") as f:
            records = json.load(f)
        
        for record in records:
            api = API(
                id=record["id"],
                endpoint=record["endpoint"],
                method=record["method"],
                owner_team=record.get("owner_team"),
                source=record["source"],
                tags=json.dumps(record.get("tags", [])),
                last_called_at=record.get("last_called_at"),
                last_deployment_at=record.get("last_deployment_at"),
                call_volume_30d=record.get("call_volume_30d", 0),
                call_volume_7d=record.get("call_volume_7d", 0),
                error_rate=record.get("error_rate", 0.0),
                response_time_p95_ms=record.get("response_time_p95_ms", 0),
                has_auth=int(record.get("has_auth", False)),
                has_encryption=int(record.get("has_encryption", False)),
                has_rate_limit=int(record.get("has_rate_limit", False)),
                has_documentation=int(record.get("has_documentation", False)),
                is_documented_in_gateway=int(record.get("is_documented_in_gateway", False)),
                version_age_days=record.get("version_age_days", 0),
                dependent_services_count=record.get("dependent_services_count", 0),
                data_sensitivity=record.get("data_sensitivity", "low"),
                ml_status="unknown",  # Scan pipeline needs to set these!
                discovered_at=record.get("discovered_at", datetime.now(timezone.utc).isoformat())
            )
            db.add(api)
        
        await db.commit()
        print(f"Successfully seeded {len(records)} APIs.")
    except Exception as e:
        print(f"Error seeding data: {e}")
        await db.rollback()
