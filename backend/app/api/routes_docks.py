import uuid
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.dock import Dock
from app.models.facility import Facility
from app.schemas.dock import DockResponse, DockUpdate
from app.services.ws_hub import ws_hub

router = APIRouter(prefix="/docks", tags=["Docks"])

class DockDirectCreate(BaseModel):
    facility_id: Optional[str] = None
    dock_number: str = Field(..., description="Örn: Rampa 01")
    dock_type: str = Field("SHELTER", description="SHELTER, COLD_REEFER, HYDRAULIC, GROUND")
    max_pallets: int = Field(33, ge=1, le=100)
    notes: Optional[str] = None

@router.get("", response_model=List[DockResponse])
async def list_all_docks(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Dock).order_by(Dock.dock_number))
    return res.scalars().all()

@router.post("", status_code=201, response_model=DockResponse)
async def create_dock(payload: DockDirectCreate, db: AsyncSession = Depends(get_db)):
    facility_id = payload.facility_id
    if not facility_id:
        res = await db.execute(select(Facility).order_by(Facility.created_at))
        facility = res.scalars().first()
        if not facility:
            raise HTTPException(status_code=400, detail="Önce bir tesis oluşturulmalıdır.")
        facility_id = facility.id

    dock = Dock(
        id=str(uuid.uuid4()),
        facility_id=facility_id,
        dock_number=payload.dock_number,
        dock_type=payload.dock_type,
        max_pallets=payload.max_pallets,
        status="IDLE",
        notes=payload.notes
    )
    db.add(dock)
    await db.commit()
    await db.refresh(dock)

    await ws_hub.broadcast_event("DOCK_CONFIG_CHANGED", {
        "facility_id": facility_id,
        "dock_id": dock.id,
        "dock_number": dock.dock_number,
        "action": "ADDED"
    })

    return dock

@router.patch("/{dock_id}/status", response_model=DockResponse)
async def update_dock_status(dock_id: str, update_data: DockUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Dock).where(Dock.id == dock_id))
    dock = res.scalars().first()
    if not dock:
        raise HTTPException(status_code=404, detail="Dock not found")

    if update_data.status:
        dock.status = update_data.status
    if update_data.is_active is not None:
        dock.is_active = update_data.is_active
    if update_data.notes:
        dock.notes = update_data.notes

    await db.commit()
    await db.refresh(dock)

    # Broadcast status change via WebSocket
    await ws_hub.broadcast_event("DOCK_STATUS_CHANGED", {
        "dock_id": dock.id,
        "dock_number": dock.dock_number,
        "status": dock.status,
        "is_active": dock.is_active
    })

    return dock

@router.delete("/{dock_id}")
async def delete_dock(dock_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Dock).where(Dock.id == dock_id))
    dock = res.scalars().first()
    if not dock:
        raise HTTPException(status_code=404, detail="Dock not found")

    facility_id = dock.facility_id
    await db.delete(dock)
    await db.commit()

    await ws_hub.broadcast_event("DOCK_CONFIG_CHANGED", {
        "facility_id": facility_id,
        "dock_id": dock_id,
        "action": "REMOVED"
    })

    return {"message": "Dock deleted successfully"}
