import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Callable, Awaitable
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
            id=wf_id,
            api_id=api_id,
            status="in_progress",
            current_step=DECOMM_STEPS[0]["id"],
            completed_steps="[]",
            initiated_by=initiated_by,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(wf)

        # Audit log
        self.db.add(AuditLog(
            actor=initiated_by,
            action="decommission_started",
            entity_type="api",
            entity_id=api_id,
            details=json.dumps({"workflow_id": wf_id}),
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        await self.db.commit()
        return wf_id

    async def execute_workflow(self, api_id: str, wf_id: str, broadcast_fn: Callable[[dict], Awaitable[None]]) -> None:
        """Run all decommission steps sequentially with broadcast updates."""
        completed = []

        for step in DECOMM_STEPS:
            await asyncio.sleep(step["delay"])
            completed.append(step["id"])

            await self.db.execute(
                update(DecommWorkflow).where(DecommWorkflow.id == wf_id).values(
                    current_step=step["id"],
                    completed_steps=json.dumps(completed),
                )
            )
            await self.db.commit()

            await broadcast_fn({
                "type": "decomm_update",
                "api_id": api_id,
                "workflow_id": wf_id,
                "current_step": step["id"],
                "completed_steps": completed,
                "step_label": step["label"],
            })

        # ── Mark API as decommissioned ────────────────────────────────
        await self.db.execute(
            update(API).where(API.id == api_id).values(
                ml_status="decommissioned",
                decommissioned_at=datetime.now(timezone.utc).isoformat(),
                is_active=0,
            )
        )
        await self.db.execute(
            update(DecommWorkflow).where(DecommWorkflow.id == wf_id).values(
                status="completed",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.db.add(AuditLog(
            actor="system",
            action="decommission_completed",
            entity_type="api",
            entity_id=api_id,
            details=json.dumps({"workflow_id": wf_id, "steps": len(DECOMM_STEPS)}),
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        await self.db.commit()
        await broadcast_fn({"type": "decomm_complete", "api_id": api_id, "workflow_id": wf_id})
