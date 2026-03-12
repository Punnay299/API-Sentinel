from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from services.api_service import APIService
from schemas.api_schema import APIResponse, APIListResponse, APIUpdateRequest

router = APIRouter()

@router.get("/", response_model=APIListResponse)
async def list_apis(
    status:     Optional[str] = Query(None, description="Filter by ML status"),
    risk:       Optional[str] = Query(None, description="Filter by risk level"),
    search:     Optional[str] = Query(None, description="Search endpoint path"),
    owner:      Optional[str] = Query(None, description="Filter by owner team"),
    source:     Optional[str] = Query(None, description="Filter by discovery source"),
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
    api = await service.update_api(api_id, body.dict(exclude_unset=True))
    if not api:
         raise HTTPException(status_code=404, detail=f"API '{api_id}' not found")
    return api

@router.post("/{api_id}/reanalyze", response_model=APIResponse)
async def reanalyze_api(api_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger fresh ML analysis for a single API."""
    from main import get_ml_engine
    service = APIService(db)
    engine  = get_ml_engine()
    api = await service.run_ml_analysis(api_id, engine)
    if not api:
        raise HTTPException(status_code=404, detail=f"API '{api_id}' not found")
    return api

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
