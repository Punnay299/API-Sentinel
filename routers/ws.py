from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from realtime.connection_manager import manager
import asyncio
from datetime import datetime, timezone

router = APIRouter()

@router.websocket("/monitor")
async def ws_monitor(ws: WebSocket):
    await manager.connect(ws)
    try:
        await manager.send(ws, {
            "type": "init",
            "message": "Connected to ZombieGuard real-time monitor",
        })

        while True:
            await asyncio.sleep(10)
            await manager.send(ws, {
                "type": "heartbeat",
                "ts": datetime.now(timezone.utc).isoformat(),
                "connections": manager.connection_count,
            })

    except WebSocketDisconnect:
        manager.disconnect(ws)
