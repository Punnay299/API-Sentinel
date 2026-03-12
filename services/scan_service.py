import asyncio
import uuid
import json
from datetime import datetime, timezone
import random
from typing import Callable, Awaitable
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
        self.db = db
        self.engine = engine

    async def create_scan(self, targets: list[str], deep_scan: bool) -> str:
        scan_id = str(uuid.uuid4())
        scan = Scan(
            id=scan_id,
            status="running",
            targets=json.dumps(targets),
            deep_scan=int(deep_scan),
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(scan)
        await self.db.commit()
        return scan_id

    async def run_scan(self, scan_id: str, broadcast_fn: Callable[[dict], Awaitable[None]]) -> None:
        """
        Full async scan pipeline.
        broadcast_fn: coroutine to push WS/SSE events to clients.
        For the hackathon, we simulate finding APIs by drawing from api_inventory.json via the DB's unknown APIs.
        """
        # 1. First, see how many total unknown APIs we have in the DB to distribute among sources.
        result = await self.db.execute(select(API).where(API.ml_status == 'unknown'))
        unknown_apis = result.scalars().all()
        total_available = len(unknown_apis)
        
        total_found = 0
        
        # We need to distribute total_available across the 6 sources.
        # If total_available is 45 (from our seed), it will split them roughly evenly.
        apis_per_source = total_available // len(SCAN_SOURCES)
        remainder = total_available % len(SCAN_SOURCES)

        for i, source in enumerate(SCAN_SOURCES):
            await asyncio.sleep(source["delay"])

            # Determine how many APIs we "found" in this batch
            if i == len(SCAN_SOURCES) - 1:
                 found = apis_per_source + remainder
            else:
                 found = apis_per_source

            if total_available == 0:
                 # If we have no unknown APIs, fall back to random finding for simulation continuity
                 found = random.randint(source["min"], source["max"])

            total_found += found
            msg = f"Scanned {source['name']} — {found} endpoints discovered"

            # Persist event
            event = ScanEvent(
                scan_id=scan_id,
                event_type="found",
                source=source["name"],
                message=msg,
                apis_found=found,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self.db.add(event)

            # Update scan progress (up to 80% for discovery phase)
            progress = int(((i + 1) / len(SCAN_SOURCES)) * 80)
            await self.db.execute(
                update(Scan).where(Scan.id == scan_id).values(
                    progress=progress, apis_found=total_found
                )
            )
            await self.db.commit()

            # Broadcast SSE event
            await broadcast_fn({
                "type": "scan_update",
                "scan_id": scan_id,
                "progress": progress,
                "apis_found": total_found,
                "source": source["name"],
                "message": msg,
            })

        # ── ML Analysis Phase ─────────────────────────────────────────
        await self._run_ml_analysis_phase(scan_id, broadcast_fn)

        # ── Finalise ──────────────────────────────────────────────────
        await self.db.execute(
            update(Scan).where(Scan.id == scan_id).values(
                status="completed",
                progress=100,
                apis_found=total_found,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        await self.db.commit()
        await broadcast_fn({"type": "scan_complete", "scan_id": scan_id, "apis_found": total_found})

    async def _run_ml_analysis_phase(self, scan_id: str, broadcast_fn: Callable[[dict], Awaitable[None]]) -> None:
        """Run ML engine over all unanalysed APIs, persist results."""
        result = await self.db.execute(
            select(API).where(API.ml_status == "unknown")
        )
        apis = result.scalars().all()
        
        if not apis:
             await broadcast_fn({
                 "type": "scan_update", 
                 "scan_id": scan_id, 
                 "progress": 90, 
                 "message": "No new APIs found requiring analysis.", 
                 "source": "ML Engine"
             })
             return

        # Announce we are starting ML Analysis
        await broadcast_fn({
             "type": "scan_update", 
             "scan_id": scan_id, 
             "progress": 85, 
             "message": f"Starting ML Analysis pipeline on {len(apis)} endpoints...", 
             "source": "ML Engine"
        })

        # Process each API
        for api in apis:
            api_dict = api.__dict__.copy()
            api_dict.pop('_sa_instance_state', None)
            
            # Use real analyze_api method (simulated as async compatible in engine.py)
            analysis = await self.engine.analyze_api(api_dict)
            
            api.ml_status = analysis["classification"]["status"]
            api.ml_confidence = float(analysis["classification"]["confidence"])
            api.ml_probabilities = json.dumps(analysis["classification"]["probabilities"])
            api.ml_security_score = analysis["security"]["security_score"]
            api.ml_risk_level = analysis["security"]["risk_level"]
            api.ml_security_issues = json.dumps(analysis["security"]["issues"])
            api.ml_is_shadow = int(analysis["shadow_detection"]["is_shadow"])
            api.ml_anomaly_score = float(analysis["shadow_detection"]["anomaly_score"])
            api.ml_analyzed_at = datetime.now(timezone.utc).isoformat()

            # Create alert for critical findings
            if api.ml_status == "zombie" or api.ml_risk_level == "critical":
                alert = Alert(
                    api_id=api.id,
                    alert_type="ZOMBIE" if api.ml_status == "zombie" else "CRITICAL",
                    severity="critical",
                    message=f"{api.endpoint} — ML classified as {api.ml_status.upper()}",
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self.db.add(alert)

        await self.db.commit()
        await broadcast_fn({
            "type": "ml_complete", 
            "scan_id": scan_id, 
            "analysed": len(apis)
        })
