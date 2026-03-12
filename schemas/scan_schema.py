from pydantic import BaseModel
from typing import Optional, List

class ScanEventSchema(BaseModel):
    event_type: str
    source: Optional[str] = None
    message: str
    apis_found: int = 0
    created_at: str

    class Config:
        from_attributes = True

class ScanResponse(BaseModel):
    id: str
    status: str
    targets: List[str] = []
    deep_scan: bool = False
    apis_found: int = 0
    progress: int = 0
    started_at: str
    completed_at: Optional[str] = None
    events: List[ScanEventSchema] = []

    class Config:
        from_attributes = True
