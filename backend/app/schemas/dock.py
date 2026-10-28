from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class DockBase(BaseModel):
    dock_number: str
    dock_type: str = "SHELTER" # SHELTER, HYDRAULIC, COLD_REEFER, GROUND
    is_active: bool = True
    max_pallets: int = 33
    status: str = "IDLE"
    notes: Optional[str] = None

class DockCreate(DockBase):
    facility_id: str

class DockUpdate(BaseModel):
    dock_number: Optional[str] = None
    dock_type: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class DockResponse(DockBase):
    id: str
    facility_id: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
