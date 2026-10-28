from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.gate_log import GateLog
from app.schemas.gate import GateCheckInRequest, GateOverrideRequest, GateCheckOutRequest, GateLogResponse
from app.services.ws_hub import ws_hub

router = APIRouter(prefix="/gate", tags=["Gate & Security"])

@router.get("/today")
async def list_today_gate_vehicles(db: AsyncSession = Depends(get_db)):
    """Güvenlik kulübesi tableti için günün beklenen ve sahadaki araçları."""
    res = await db.execute(
        select(Appointment)
        .where(Appointment.status.in_(["SCHEDULED", "WAITING_LOT", "CALLED", "UNLOADING", "COMPLETED"]))
        .order_by(Appointment.slot_start)
    )
    return res.scalars().all()

@router.post("/check-in")
async def gate_check_in(req: GateCheckInRequest, db: AsyncSession = Depends(get_db)):
    """Nizamiye kapı kontrolü: Plaka veya QR token sorgusuyla tır parkına (Buffer Lot) kabul."""
    clean_query = req.plate_or_token.upper().strip().replace(" ", "")
    
    # Query appointment using SQL func.replace and case insensitivity
    res = await db.execute(
        select(Appointment).where(
            or_(
                func.replace(Appointment.vehicle_plate, " ", "") == clean_query,
                Appointment.vehicle_plate == req.plate_or_token.strip(),
                Appointment.tracking_token == req.plate_or_token.strip()
            )
        )
    )
    app = res.scalars().first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail=f"'{req.plate_or_token}' plakasına veya referans koduna ait aktif randevu bulunamadı."
        )

    # Idempotency check
    if req.idempotency_key:
        log_res = await db.execute(select(GateLog).where(GateLog.idempotency_key == req.idempotency_key))
        if log_res.scalars().first():
            return {"message": "İşlem daha önce işlendi (Idempotent).", "appointment": app}

    # Update appointment status to WAITING_LOT
    app.status = "WAITING_LOT"
    app.actual_gate_in = datetime.now()

    # Create GateLog
    log = GateLog(
        appointment_id=app.id,
        event_type="GATE_IN",
        gate_operator=req.operator or "Nizamiye-01",
        idempotency_key=req.idempotency_key,
        notes=f"Araç kapıdan içeri alındı. Tır parkına yönlendirildi."
    )
    db.add(log)
    await db.commit()

    # Broadcast to Rampa Amiri and TV Displays
    await ws_hub.broadcast_event("VEHICLE_ARRIVED_AT_GATE", {
        "appointment_id": app.id,
        "vehicle_plate": app.vehicle_plate,
        "carrier_name": app.carrier_name,
        "actual_gate_in": app.actual_gate_in.isoformat(),
        "status": app.status
    })

    return {
        "message": f"Araç kabul edildi: {app.vehicle_plate} -> Tır Parkı Bölge B",
        "appointment_id": app.id,
        "status": app.status,
        "carrier": app.carrier_name
    }

@router.post("/override")
async def gate_override(req: GateOverrideRequest, db: AsyncSession = Depends(get_db)):
    """Plaka veya şoför uyuşmazlığında denetimli geçiş (Fotoğraflı & Sebepli Override)"""
    res = await db.execute(select(Appointment).where(Appointment.id == req.appointment_id))
    app = res.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    old_plate = app.vehicle_plate
    app.vehicle_plate = req.actual_plate.upper().strip()
    if req.driver_name:
        app.driver_name = req.driver_name
    if req.driver_phone:
        app.driver_phone = req.driver_phone

    app.status = "WAITING_LOT"
    app.actual_gate_in = datetime.now()

    # Gerçek Fotoğraf Kaydı (Audit Trail Güvenliği):
    saved_photo_path = None
    if req.override_photo_base64:
        try:
            import base64
            from pathlib import Path
            upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "gate_overrides"
            upload_dir.mkdir(parents=True, exist_ok=True)
            photo_filename = f"override_{app.id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            file_path = upload_dir / photo_filename
            clean_b64 = req.override_photo_base64.split(",")[-1]
            file_path.write_bytes(base64.b64decode(clean_b64))
            saved_photo_path = f"/uploads/gate_overrides/{photo_filename}"
        except Exception as e:
            logger.warning(f"Override fotoğrafı kaydedilemedi: {e}")
            saved_photo_path = f"saved_override_{app.id[:8]}.jpg"

    log = GateLog(
        appointment_id=app.id,
        event_type="OVERRIDE_PLATE",
        gate_operator=req.operator or "Nizamiye-01",
        override_reason=req.override_reason,
        override_photo_url=saved_photo_path,
        notes=f"Plaka {old_plate} -> {app.vehicle_plate} olarak revize edildi. Sebep: {req.override_reason}"
    )
    db.add(log)
    await db.commit()

    await ws_hub.broadcast_event("GATE_OVERRIDE_EXECUTED", {
        "appointment_id": app.id,
        "original_plate": old_plate,
        "actual_plate": app.vehicle_plate,
        "reason": req.override_reason
    })

    return {
        "message": f"Denetimli geçiş onaylandı. Yeni plaka: {app.vehicle_plate}",
        "status": app.status
    }

@router.post("/check-out")
async def gate_check_out(req: GateCheckOutRequest, db: AsyncSession = Depends(get_db)):
    """Araç sahadan ayrıldı (Gate-Out). Karayolları aks/tonaj güvenlik kilidi denetlenir."""
    res = await db.execute(select(Appointment).where(Appointment.id == req.appointment_id))
    app = res.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # KGM Karayolları Aks ve Tonaj Güvenlik Kilidi (P1 High)
    if app.weighbridge_discrepancy and not req.force_override:
        raise HTTPException(
            status_code=409,
            detail=(
                f"KGM YASAL TONAJ & AKS KİLİDİ: '{app.vehicle_plate}' plakalı araç, kantar tartımında Karayolları azami "
                f"yüklü ağırlık veya aks (11.5 ton) sınırını aşmıştır! Saha amiri ve kantar operatörü yük dengeleme "
                f"(rebalance) tutanağı düzenlemeden aracın tesisten otoyola çıkışına izin verilemez."
            )
        )

    app.status = "DEPARTED"
    app.actual_gate_out = datetime.now()

    note_text = req.notes or "Araç sahadan ayrıldı."
    if app.weighbridge_discrepancy and req.force_override:
        note_text += f" [KGM TONAJ AŞIMI İDARİ OVERRIDE]: {req.override_reason or 'Operatör denetimli izin'}"

    log = GateLog(
        appointment_id=app.id,
        event_type="GATE_OUT",
        gate_operator=req.operator or "Nizamiye-01",
        override_reason=req.override_reason if (app.weighbridge_discrepancy and req.force_override) else None,
        notes=note_text
    )
    db.add(log)
    await db.commit()

    await ws_hub.broadcast_event("VEHICLE_DEPARTED", {
        "appointment_id": app.id,
        "vehicle_plate": app.vehicle_plate
    })

    return {"message": "Çıkış onaylandı.", "status": app.status}
