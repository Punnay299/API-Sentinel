from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.connection import get_db
from database.models import API, Scan

router = APIRouter()

@router.get("/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    # Total APIs
    total = await db.scalar(select(func.count(API.id)))
    
    # Needs Python logic to group by since it's easier than raw SQL for JSON fields
    result = await db.execute(select(API))
    apis = result.scalars().all()
    
    status_breakdown = {"active": 0, "deprecated": 0, "orphaned": 0, "zombie": 0, "shadow": 0, "unknown": 0, "decommissioned": 0}
    risk_breakdown = {"low": 0, "medium": 0, "high": 0, "critical": 0, "unknown": 0}
    
    total_score = 0
    shadow_count = 0
    
    for api in apis:
        status_breakdown[api.ml_status] = status_breakdown.get(api.ml_status, 0) + 1
        risk_breakdown[api.ml_risk_level] = risk_breakdown.get(api.ml_risk_level, 0) + 1
        total_score += api.ml_security_score
        if api.ml_is_shadow:
            shadow_count += 1
            
    avg_score = (total_score / len(apis)) if apis else 0
    zombie_pct = (status_breakdown["zombie"] / len(apis)) * 100 if apis else 0
    
    scans_completed = await db.scalar(select(func.count(Scan.id)).where(Scan.status == "completed"))

    return {
        "total_apis": total,
        "status_breakdown": status_breakdown,
        "risk_breakdown": risk_breakdown,
        "avg_security_score": round(avg_score, 1),
        "zombie_percentage": round(zombie_pct, 1),
        "shadow_count": shadow_count,
        "critical_apis": risk_breakdown.get("critical", 0),
        "scans_completed": scans_completed or 0
    }
