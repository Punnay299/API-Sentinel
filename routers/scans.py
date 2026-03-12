import asyncio
import json
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from database.connection import get_db
from services.scan_service import ScanService
from schemas.scan_schema import ScanResponse

router = APIRouter()

class ScanStartRequest(BaseModel):
    targets: List[str] = ["api_gateway", "github", "k8s", "lambda"]
    deep_scan: bool = False

# We need an internal pub/sub or queue structure to stream from the background task to the HTTP response
# For simplicity in this non-distributed setup, we will use a global dict mapping scan_id to an asyncio.Queue
scan_queues: dict[str, asyncio.Queue] = {}

async def scan_broadcaster(scan_id: str, data: dict):
    if scan_id in scan_queues:
        await scan_queues[scan_id].put(data)
    
    # Also broadcast via websockets if needed, but the design implies scan streams are SSE
    from realtime.connection_manager import manager
    if data.get("type") in ["scan_complete", "ml_complete"] or data.get("severity") == "critical":
        await manager.broadcast(data)

@router.post("/start")
async def start_scan(
    request: ScanStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    from main import get_ml_engine
    engine = get_ml_engine()
    service = ScanService(db, engine)
    
    scan_id = await service.create_scan(request.targets, request.deep_scan)
    
    # Initialize queue for this scan
    scan_queues[scan_id] = asyncio.Queue()

    # Create a small wrapper function to run the scan in the background
    async def run_scan_bg(sid: str):
         # Create a new session for the background task
         from database.connection import AsyncSessionLocal
         async with AsyncSessionLocal() as bg_db:
             bg_service = ScanService(bg_db, engine)
             try:
                 async def bcast(data):
                     await scan_broadcaster(sid, data)
                 await bg_service.run_scan(sid, bcast)
             finally:
                 # Clean up the queue after some time so we don't leak memory, 
                 # or when the stream disconnects. Putting a sentinel value.
                 await scan_broadcaster(sid, {"type": "_close"})

    background_tasks.add_task(run_scan_bg, scan_id)
    return {"scan_id": scan_id}

@router.get("/{scan_id}/stream")
async def stream_scan(scan_id: str):
    """
    Server-Sent Events endpoint for a scan.
    """
    if scan_id not in scan_queues:
        # If the scan was already finished or does not exist
        # Depending on requirements we could fetch it from DB and send it instantly
        # For now, create an empty queue
        scan_queues[scan_id] = asyncio.Queue()

    async def event_generator():
        try:
            while True:
                data = await scan_queues[scan_id].get()
                if data.get("type") == "_close":
                    break
                
                # Fetch current scan status from DB to form the full ScanRecord payload
                # In a real app we'd build this in the broadcaster, but for architecture purity:
                from database.connection import AsyncSessionLocal
                from database.models import Scan
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Scan).options(selectinload(Scan.events)).where(Scan.id == scan_id)
                    )
                    scan = result.scalar_one_or_none()
                    if scan:
                        # Serialize to match frontend expectation
                        payload = {
                            "id": scan.id,
                            "status": scan.status,
                            "targets": json.loads(scan.targets) if scan.targets else [],
                            "progress": scan.progress,
                            "apis_found": scan.apis_found,
                            "started_at": scan.started_at,
                            "completed_at": scan.completed_at,
                            "events": [
                                {
                                    "event_type": e.event_type,
                                    "source": e.source,
                                    "message": e.message,
                                    "apis_found": e.apis_found,
                                    "created_at": e.created_at
                                } for e in scan.events
                            ]
                        }
                        
                        # Yield the event formatted as an SSE
                        yield f"data: {json.dumps(payload)}\n\n"
                    
                if data.get("type") == "scan_complete":
                    break
        finally:
            # When client disconnects or scan finishes
            if scan_id in scan_queues:
                del scan_queues[scan_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")
