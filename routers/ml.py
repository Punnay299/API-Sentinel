from fastapi import APIRouter
import json
from datetime import datetime, timezone
import os
import joblib

router = APIRouter()

@router.post("/retrain")
async def retrain_models():
    """Trigger a full retraining of all models."""
    from main import get_ml_engine
    engine = get_ml_engine()
    
    # Normally this would be a background task as it blocks, 
    # but for hackathon / demonstration we wait for it.
    engine.train()
    
    # Save manually
    path = "models/engine.pkl"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(engine, path)
    
    from realtime.connection_manager import manager
    await manager.broadcast({
        "type": "ml_retrained",
        "ts": datetime.now(timezone.utc).isoformat(),
        "message": "Global ML Models have been successfully retrained."
    })
    
    return {"status": "success", "message": "Models retrained successfully"}

@router.get("/status")
async def model_status():
    return {
        "status": "active",
        "classifier_version": "RandomForest-v1",
        "shadow_version": "IsolationForest-v1",
        "security_version": "GradientBoosting-v1",
        "last_trained": datetime.now(timezone.utc).isoformat()  # Mocked dynamic timestamp for demo simplicity
    }
