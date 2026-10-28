import uuid
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.facility import Facility
from app.models.dock import Dock
from app.schemas.dock import DockResponse
from app.services.ws_hub import ws_hub

router = APIRouter(prefix="/facilities", tags=["Facilities & Docks"])

class DockCreatePayload(BaseModel):
    dock_number: str = Field(..., description="Örn: Rampa 01")
    dock_type: str = Field("SHELTER", description="SHELTER, COLD_REEFER, HYDRAULIC, GROUND")
    max_pallets: int = Field(33, ge=1, le=100)
    notes: Optional[str] = None

class FacilityCreatePayload(BaseModel):
    name: str = Field(..., description="Tesis Adı, örn: Merkez Dağıtım Deposu")
    code: Optional[str] = Field(None, description="Kısa kod, örn: DC-01")
    address: Optional[str] = None
    latitude: Optional[float] = 40.8524
    longitude: Optional[float] = 29.3812
    geofence_radius_meters: Optional[int] = 500
    timezone: Optional[str] = "Europe/Istanbul"
    default_quantum_minutes: Optional[int] = 15
    docks: Optional[List[DockCreatePayload]] = []

class FacilityUpdatePayload(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius_meters: Optional[int] = None
    timezone: Optional[str] = None
    default_quantum_minutes: Optional[int] = None

@router.get("")
async def list_facilities(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Facility).order_by(Facility.created_at))
    return res.scalars().all()

@router.post("", status_code=201)
async def create_facility(payload: FacilityCreatePayload, db: AsyncSession = Depends(get_db)):
    code = payload.code
    if not code:
        clean_name = "".join(c for c in payload.name if c.isalnum()).upper()[:6]
        code = f"{clean_name or 'FAC'}-{uuid.uuid4().hex[:4].upper()}"

    existing = await db.execute(select(Facility).where(Facility.code == code))
    if existing.scalars().first():
        code = f"{code}-{uuid.uuid4().hex[:3].upper()}"

    facility = Facility(
        id=str(uuid.uuid4()),
        code=code,
        name=payload.name,
        address=payload.address,
        latitude=payload.latitude or 40.8524,
        longitude=payload.longitude or 29.3812,
        geofence_radius_meters=payload.geofence_radius_meters or 500,
        timezone=payload.timezone or "Europe/Istanbul",
        default_quantum_minutes=payload.default_quantum_minutes or 15
    )
    db.add(facility)
    await db.flush()

    if payload.docks:
        for d in payload.docks:
            dock = Dock(
                id=str(uuid.uuid4()),
                facility_id=facility.id,
                dock_number=d.dock_number,
                dock_type=d.dock_type,
                max_pallets=d.max_pallets,
                status="IDLE",
                notes=d.notes
            )
            db.add(dock)

    await db.commit()
    await db.refresh(facility)

    await ws_hub.broadcast_event("FACILITY_CONFIG_CHANGED", {
        "facility_id": facility.id,
        "name": facility.name,
        "code": facility.code
    })

    return facility

@router.get("/{facility_id}")
async def get_facility(facility_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Facility).where(Facility.id == facility_id))
    facility = res.scalars().first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility

@router.patch("/{facility_id}")
async def update_facility(facility_id: str, payload: FacilityUpdatePayload, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Facility).where(Facility.id == facility_id))
    facility = res.scalars().first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    if payload.name is not None:
        facility.name = payload.name
    if payload.code is not None:
        facility.code = payload.code
    if payload.address is not None:
        facility.address = payload.address
    if payload.latitude is not None:
        facility.latitude = payload.latitude
    if payload.longitude is not None:
        facility.longitude = payload.longitude
    if payload.geofence_radius_meters is not None:
        facility.geofence_radius_meters = payload.geofence_radius_meters
    if payload.timezone is not None:
        facility.timezone = payload.timezone
    if payload.default_quantum_minutes is not None:
        facility.default_quantum_minutes = payload.default_quantum_minutes

    await db.commit()
    await db.refresh(facility)

    await ws_hub.broadcast_event("FACILITY_CONFIG_CHANGED", {
        "facility_id": facility.id,
        "name": facility.name,
        "code": facility.code
    })

    return facility

@router.delete("/{facility_id}")
async def delete_facility(facility_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Facility).where(Facility.id == facility_id))
    facility = res.scalars().first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    await db.delete(facility)
    await db.commit()

    await ws_hub.broadcast_event("FACILITY_CONFIG_CHANGED", {
        "action": "DELETED",
        "facility_id": facility_id
    })

    return {"message": "Facility deleted successfully"}

@router.get("/{facility_id}/docks", response_model=List[DockResponse])
async def list_facility_docks(facility_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Dock).where(Dock.facility_id == facility_id).order_by(Dock.dock_number))
    return res.scalars().all()

@router.post("/{facility_id}/docks", status_code=201, response_model=DockResponse)
async def add_dock_to_facility(facility_id: str, payload: DockCreatePayload, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Facility).where(Facility.id == facility_id))
    facility = res.scalars().first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    dock = Dock(
        id=str(uuid.uuid4()),
        facility_id=facility.id,
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

@router.delete("/{facility_id}/docks/{dock_id}")
async def remove_dock_from_facility(facility_id: str, dock_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Dock).where(Dock.id == dock_id, Dock.facility_id == facility_id))
    dock = res.scalars().first()
    if not dock:
        raise HTTPException(status_code=404, detail="Dock not found")

    await db.delete(dock)
    await db.commit()

    await ws_hub.broadcast_event("DOCK_CONFIG_CHANGED", {
        "facility_id": facility_id,
        "dock_id": dock_id,
        "action": "REMOVED"
    })

    return {"message": "Dock removed successfully"}
