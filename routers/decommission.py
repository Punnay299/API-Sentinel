from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from database.connection import get_db
from database.models import DecommWorkflow
from services.decomm_service import DecommService

router = APIRouter()

async def decomm_broadcaster(data: dict):
    from realtime.connection_manager import manager
    await manager.broadcast(data)

@router.post("/{api_id}/start")
async def start_decommission(
    api_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    service = DecommService(db)
    # Validate API exists? Skipped for brevity, assume valid.
    
    # Check if workflow already running
    result = await db.execute(select(DecommWorkflow).where(DecommWorkflow.api_id == api_id))
    existing = result.scalar_one_or_none()
    if existing and existing.status in ["pending", "in_progress"]:
         raise HTTPException(status_code=400, detail="Decommission workflow already in progress.")

    wf_id = await service.start_workflow(api_id)

    async def run_wf_bg(a_id: str, w_id: str):
        from database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_db:
            bg_service = DecommService(bg_db)
            await bg_service.execute_workflow(a_id, w_id, decomm_broadcaster)

    background_tasks.add_task(run_wf_bg, api_id, wf_id)
    
    return await get_decommission_status(api_id, db)

@router.get("/{api_id}")
async def get_decommission_status(api_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DecommWorkflow).where(DecommWorkflow.api_id == api_id)
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="No decommission workflow found for this API.")
        
    return {
        "id": wf.id,
        "api_id": wf.api_id,
        "status": wf.status,
        "current_step": wf.current_step,
        "completed_steps": json.loads(wf.completed_steps) if wf.completed_steps else [],
        "started_at": wf.started_at,
        "completed_at": wf.completed_at
    }
