from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os

from database.connection import init_db, get_db, AsyncSessionLocal
from routers import apis, scans, analytics, decommission, ml as ml_router, ws
from services.api_service import seed_initial_data
from ml.engine import ZombieAPIMLEngine

# ── Global ML Engine ─────────────────────────────────────────────────────────
_engine: ZombieAPIMLEngine | None = None

def get_ml_engine() -> ZombieAPIMLEngine:
    global _engine
    if _engine is None:
        _engine = ZombieAPIMLEngine.load_or_train()
    return _engine

# ── Lifespan (replaces on_event startup/shutdown) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("Initialising database...")
    await init_db()
    
    print("Loading/training ML models...")
    # Wrap synchronous ML loading in a thread to not block the event loop entirely during boot
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_ml_engine)
    
    print("Seeding initial API inventory...")
    engine = get_ml_engine()
    async with AsyncSessionLocal() as session:
        await seed_initial_data(engine, session)
        
    print("✓ ZombieGuard ready.")
    yield
    # SHUTDOWN
    print("Shutting down ZombieGuard...")

# ── App Factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title       = "ZombieGuard API",
        description = "Zombie API Discovery & Defence Platform",
        version     = "1.0.0",
        lifespan    = lifespan,
        docs_url    = "/docs",
        redoc_url   = "/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["*"],  # Open CORS for hackathon
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # Mount routers
    app.include_router(apis.router,          prefix="/apis",        tags=["APIs"])
    app.include_router(scans.router,         prefix="/scan",        tags=["Scanning"])
    app.include_router(analytics.router,     prefix="/analytics",   tags=["Analytics"])
    app.include_router(decommission.router,  prefix="/decommission",tags=["Decommission"])
    app.include_router(ml_router.router,     prefix="/ml",          tags=["ML Engine"])
    app.include_router(ws.router,            prefix="/ws",          tags=["WebSockets"])

    @app.get("/health", tags=["System"])
    async def health():
        engine = get_ml_engine()
        # The engine in this design doesn't have a specific `trained` flag as an attribute, 
        # but loading it guarantees it is trained.
        return {
            "status": "healthy",
            "ml_trained": True, 
            "version": "1.0.0",
        }

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
