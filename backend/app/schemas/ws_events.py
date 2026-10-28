from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime

class WsEventMessage(BaseModel):
    event_type: str # APPOINTMENT_CREATED, VEHICLE_ARRIVED, VEHICLE_CALLED, DOCK_STATUS_CHANGED, DOCULOG_PARSED, etc.
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any]
