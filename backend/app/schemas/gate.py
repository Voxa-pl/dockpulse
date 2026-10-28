from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class GateCheckInRequest(BaseModel):
    plate_or_token: str # Can be "34 VR 8902" or "RR-9842"
    operator: Optional[str] = "Nizamiye-01"
    idempotency_key: Optional[str] = None

class GateOverrideRequest(BaseModel):
    appointment_id: str
    actual_plate: str
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    override_reason: str
    override_photo_base64: Optional[str] = None
    operator: Optional[str] = "Nizamiye-01"

class GateCheckOutRequest(BaseModel):
    appointment_id: str
    operator: Optional[str] = "Nizamiye-01"
    notes: Optional[str] = None
    force_override: Optional[bool] = False
    override_reason: Optional[str] = None

class GateLogResponse(BaseModel):
    id: str
    appointment_id: Optional[str] = None
    event_type: str
    timestamp: datetime
    gate_operator: str
    override_reason: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
