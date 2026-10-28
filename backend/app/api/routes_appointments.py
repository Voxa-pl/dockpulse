from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc, asc
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import io
import csv

from app.core.database import get_db, AsyncSessionLocal
from app.models.appointment import Appointment
from app.models.dock import Dock
from app.models.gate_log import GateLog
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptItem
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    CallToDockRequest,
    GoodsReceiptSave
)
from app.services.quantum_slot_engine import QuantumSlotEngine
from app.services.doculog_bridge import DocuLogBridge
from app.services.ws_hub import ws_hub

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.get("", response_model=List[AppointmentResponse])
async def list_appointments(
    status: Optional[str] = None,
    dock_id: Optional[str] = None,
    carrier: Optional[str] = None,
    date: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "slot_start",
    sort_order: Optional[str] = "asc",
    db: AsyncSession = Depends(get_db)
):
    query = select(Appointment)
    if status and status != "ALL":
        query = query.where(Appointment.status == status)
    if dock_id and dock_id != "ALL":
        query = query.where(Appointment.dock_id == dock_id)
    if carrier and carrier != "ALL":
        query = query.where(Appointment.carrier_name.ilike(f"%{carrier}%"))
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            next_date = target_date + timedelta(days=1)
            query = query.where(Appointment.slot_start >= datetime.combine(target_date, datetime.min.time()))
            query = query.where(Appointment.slot_start < datetime.combine(next_date, datetime.min.time()))
        except ValueError:
            pass
    if search:
        s = f"%{search.strip().upper()}%"
        query = query.where(
            or_(
                Appointment.vehicle_plate.ilike(s),
                Appointment.trailer_plate.ilike(s),
                Appointment.carrier_name.ilike(s),
                Appointment.driver_name.ilike(s),
                Appointment.po_number.ilike(s),
                Appointment.tracking_token.ilike(s)
            )
        )
    
    # Sorting
    sort_col = getattr(Appointment, sort_by, Appointment.slot_start)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))
    
    res = await db.execute(query)
    return res.scalars().all()

@router.get("/export")
async def export_appointments_report(
    status: Optional[str] = None,
    dock_id: Optional[str] = None,
    carrier: Optional[str] = None,
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Vardiya amiri ve lojistik direktörü için Excel uyumlu CSV dökümü."""
    query = select(Appointment)
    if status and status != "ALL":
        query = query.where(Appointment.status == status)
    if dock_id and dock_id != "ALL":
        query = query.where(Appointment.dock_id == dock_id)
    if carrier and carrier != "ALL":
        query = query.where(Appointment.carrier_name.ilike(f"%{carrier}%"))
    query = query.order_by(Appointment.slot_start)
    
    res = await db.execute(query)
    apps = res.scalars().all()

    # Docks lookup
    docks_res = await db.execute(select(Dock))
    docks_map = {d.id: d.dock_number for d in docks_res.scalars().all()}

    output = io.StringIO()
    # Write UTF-8 BOM for Excel compatibility
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')

    headers = [
        "Randevu ID", "Plaka", "Dorse", "Taşıyıcı Firma", "Şoför Adı", "Şoför Telefon",
        "Slot Başlangıç", "Slot Bitiş", "Atanan Rampa", "Durum",
        "Kapı Giriş (Gate-in)", "Rampa Çağrı", "Boşaltma Bitiş", "Kapı Çıkış (Gate-out)",
        "Saha Kalış Süresi (Dwell - dk)", "Palet Adedi", "Yük Tipi", "PO No",
        "DocuLog İrsaliye ID", "DocuLog AI Durumu", "Takip Kodu"
    ]
    writer.writerow(headers)

    for a in apps:
        dwell_time = ""
        if a.actual_gate_in:
            end_time = a.actual_gate_out or datetime.now()
            dwell_time = int((end_time - a.actual_gate_in).total_seconds() / 60)

        writer.writerow([
            a.id[:8],
            a.vehicle_plate,
            a.trailer_plate or "-",
            a.carrier_name,
            a.driver_name,
            a.driver_phone,
            a.slot_start.strftime("%Y-%m-%d %H:%M") if a.slot_start else "",
            a.slot_end.strftime("%Y-%m-%d %H:%M") if a.slot_end else "",
            docks_map.get(a.dock_id, "Atanmadı"),
            a.status,
            a.actual_gate_in.strftime("%H:%M") if a.actual_gate_in else "-",
            a.actual_dock_in.strftime("%H:%M") if a.actual_dock_in else "-",
            a.actual_dock_out.strftime("%H:%M") if a.actual_dock_out else "-",
            a.actual_gate_out.strftime("%H:%M") if a.actual_gate_out else "-",
            dwell_time,
            a.estimated_pallets,
            a.load_type,
            a.po_number or "-",
            a.doculog_document_id or "-",
            a.doculog_status,
            a.tracking_token
        ])

    output.seek(0)
    filename = f"RampaRandevu_Vardiya_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/track/{token}")
async def get_driver_tracking(token: str, db: AsyncSession = Depends(get_db)):
    """Şoför için Zero-App hafif mobil takip bilgisi (Takip kodu veya Plaka ile arama)."""
    from sqlalchemy import func
    clean_token = token.strip().upper().replace(" ", "")
    res = await db.execute(
        select(Appointment).where(
            or_(
                Appointment.tracking_token == token.strip().upper(),
                Appointment.vehicle_plate == token.strip().upper(),
                func.replace(Appointment.vehicle_plate, " ", "") == clean_token,
                Appointment.id == token.strip()
            )
        )
    )
    app = res.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="Geçersiz veya süresi dolmuş takip bağlantısı / plaka bulunamadı")

    dock_name = None
    if app.dock_id:
        d_res = await db.execute(select(Dock).where(Dock.id == app.dock_id))
        d = d_res.scalars().first()
        if d:
            dock_name = d.dock_number

    # Calculate queue position if waiting
    queue_pos = 0
    if app.status == "WAITING_LOT":
        waiting_res = await db.execute(
            select(Appointment)
            .where(Appointment.status == "WAITING_LOT")
            .where(Appointment.actual_gate_in <= app.actual_gate_in)
        )
        queue_pos = len(waiting_res.scalars().all())

    return {
        "id": app.id,
        "carrier_name": app.carrier_name,
        "vehicle_plate": app.vehicle_plate,
        "driver_name": app.driver_name,
        "slot_start": app.slot_start.strftime("%H:%M"),
        "status": app.status,
        "assigned_dock": dock_name,
        "queue_position": queue_pos,
        "estimated_pallets": app.estimated_pallets,
        "doculog_status": app.doculog_status,
        "instructions": (
            "Lütfen Tır Parkı Bölge B'de bekleyiniz. Çağrıldığınızda rampa amiri ekrandan onaylayacaktır."
            if app.status == "WAITING_LOT"
            else f"LÜTFEN DERHAL {dock_name} NOLU RAMPAYA YANAŞINIZ!"
            if app.status == "CALLED"
            else "Körüke yanaşıldı, boşaltma işlemi devam ediyor."
            if app.status == "UNLOADING"
            else "İşlem tamamlandı, çıkış kapısına yönelebilirsiniz."
            if app.status == "COMPLETED"
            else "Randevunuz kayıtlıdır, kapı saatinde tesise geliniz."
        )
    }

@router.post("", response_model=AppointmentResponse)
async def create_appointment(
    payload: AppointmentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # 1. Calculate dynamic slot duration using Quantum Engine
    duration_minutes = QuantumSlotEngine.calculate_slot_duration(
        payload.estimated_pallets,
        payload.load_type
    )
    
    slot_start = payload.slot_start
    slot_end = payload.slot_end or (slot_start + timedelta(minutes=duration_minutes))

    # 2. Create appointment record
    app = Appointment(
        carrier_name=payload.carrier_name,
        vehicle_plate=payload.vehicle_plate.upper().strip(),
        trailer_plate=payload.trailer_plate.upper().strip() if payload.trailer_plate else None,
        driver_name=payload.driver_name,
        driver_phone=payload.driver_phone,
        driver_tckn=payload.driver_tckn,
        slot_start=slot_start,
        slot_end=slot_end,
        dock_id=payload.dock_id,
        load_type=payload.load_type,
        estimated_pallets=payload.estimated_pallets,
        calculated_duration_minutes=duration_minutes,
        po_number=payload.po_number,
        status="SCHEDULED",
        doculog_status="PENDING" if payload.waybill_image_base64 else "NOT_UPLOADED"
    )

    db.add(app)
    await db.commit()
    await db.refresh(app)

    # 3. Asynchronous DocuLog Ingestion if waybill image was uploaded
    if payload.waybill_image_base64:
        async def process_doculog():
            parsed_data = await DocuLogBridge.async_ingest_waybill(
                app.id, 
                payload.waybill_image_base64,
                cargo_type=app.cargo_type,
                carrier_name=app.carrier_name
            )
            # update db with dedicated session (avoid generator context crash)
            async with AsyncSessionLocal() as bg_db:
                res = await bg_db.execute(select(Appointment).where(Appointment.id == app.id))
                target_app = res.scalars().first()
                if target_app and parsed_data.get("status") == "PARSED":
                    target_app.doculog_status = "MATCH_OK"
                    target_app.doculog_document_id = parsed_data.get("doculog_document_id")
                    target_app.doculog_summary = parsed_data.get("summary")
                    await bg_db.commit()

                    # Notify frontend via WebSocket
                    await ws_hub.broadcast_event("DOCULOG_WAYBILL_MATCHED", {
                        "appointment_id": app.id,
                        "doculog_document_id": parsed_data.get("doculog_document_id"),
                        "summary": parsed_data.get("summary")
                    })

        background_tasks.add_task(process_doculog)

    # 4. Broadcast event
    await ws_hub.broadcast_event("APPOINTMENT_CREATED", {
        "appointment_id": app.id,
        "plate": app.vehicle_plate,
        "carrier": app.carrier_name,
        "slot_start": app.slot_start.isoformat(),
        "duration": app.calculated_duration_minutes
    })

    return app

@router.post("/{appointment_id}/call-to-dock")
async def call_vehicle_to_dock(
    appointment_id: str,
    req: CallToDockRequest,
    db: AsyncSession = Depends(get_db)
):
    """Rampa Amiri: Şoföre Rampa Tahsis Et ve Çağrı Yap (SMS/WhatsApp simülasyonu)"""
    res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    app = res.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Sıkı Saha Kuralı: Araç yalnızca tır parkında bekliyor (WAITING_LOT) ise rampaya çağrılabilir!
    # Tesis dışındaki (SCHEDULED) araç doğrudan rampaya çağrılamaz, önce kapıdan girmelidir.
    if app.status != "WAITING_LOT":
        raise HTTPException(
            status_code=400,
            detail=f"Saha Güvenlik Kuralı: Araç henüz nizamiye kapısından içeri girmemiş! (Mevcut Statü: {app.status}). Yalnızca tır parkında (WAITING_LOT) bekleyen araçlar rampaya çağrılabilir."
        )

    dock_res = await db.execute(select(Dock).where(Dock.id == req.dock_id))
    dock = dock_res.scalars().first()
    if not dock:
        raise HTTPException(status_code=404, detail="Dock not found")

    # Update Appointment
    app.dock_id = dock.id
    app.status = "CALLED"
    app.actual_dock_in = datetime.now()
    
    # Update Dock Status
    dock.status = "CALLING"

    # Add Gate Log
    log = GateLog(
        appointment_id=app.id,
        event_type="CALL_TO_DOCK",
        gate_operator=req.assigned_by or "Rampa Amiri",
        notes=f"Araç {dock.dock_number} nolu rampaya çağrıldı."
    )
    db.add(log)
    await db.commit()

    # Broadcast Realtime Event
    await ws_hub.broadcast_event("VEHICLE_CALLED_TO_DOCK", {
        "appointment_id": app.id,
        "vehicle_plate": app.vehicle_plate,
        "driver_phone": app.driver_phone,
        "dock_id": dock.id,
        "dock_number": dock.dock_number,
        "tracking_token": app.tracking_token
    })

    return {
        "message": f"{app.vehicle_plate} plakalı araç {dock.dock_number} nolu rampaya çağrıldı.",
        "status": app.status,
        "dock_number": dock.dock_number
    }

from pydantic import BaseModel

class StartOperationRequest(BaseModel):
    driver_lat: Optional[float] = None
    driver_lng: Optional[float] = None
    bypass_geofence: Optional[bool] = False

@router.post("/{appointment_id}/start-operation")
async def start_operation(
    appointment_id: str,
    req: Optional[StartOperationRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """Rampa körüğüne yanaşıldı, Geofence ve takoz emniyeti teyit edildi, boşaltma başlatıldı."""
    res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    app = res.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Çift Taraflı Handshake: Araç rampaya çağrılmış (CALLED) olmalıdır
    if app.status not in ("CALLED", "DOCKING"):
        raise HTTPException(
            status_code=400,
            detail=f"Güvenlik Doğrulaması: Araç rampaya atanmadan/çağrılmadan (Mevcut Statü: {app.status}) boşaltma başlatılamaz! Araç önce nizamiye kapısından girmeli ve rampaya yönlendirilmelidir."
        )

    # Backend Geofence Doğrulaması (GOSB DC-01: 40.8524° N, 29.3812° E)
    dist_note = "Saha Sensörü / Simülasyon"
    if req and req.driver_lat is not None and req.driver_lng is not None:
        import math
        dc_lat, dc_lng = 40.8524, 29.3812
        r = 6371000 # metre
        p1, p2 = math.radians(req.driver_lat), math.radians(dc_lat)
        dp = math.radians(dc_lat - req.driver_lat)
        dl = math.radians(dc_lng - req.driver_lng)
        a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance_meters = round(r * c)

        if distance_meters > 500 and not req.bypass_geofence:
            raise HTTPException(
                status_code=400,
                detail=f"GEOFENCE İHLALİ: Cihazınız tesis sahasının dışındadır (Mesafe: {distance_meters}m). Rampa yanaşma onayı için Gebze DC sahasında olmanız gerekir."
            )
        dist_note = f"GPS Doğrulandı: {distance_meters}m (Lat: {req.driver_lat:.4f}, Lng: {req.driver_lng:.4f})"

    app.status = "UNLOADING"
    if app.dock_id:
        dock_res = await db.execute(select(Dock).where(Dock.id == app.dock_id))
        dock = dock_res.scalars().first()
        if dock:
            dock.status = "OCCUPIED"

    db.add(GateLog(
        appointment_id=app.id,
        event_type="UNLOAD_START",
        notes=f"Körük kilitlendi, takoz switchi aktif. {dist_note}. Forklift boşaltma başladı."
    ))
    await db.commit()

    await ws_hub.broadcast_event("DOCK_OPERATION_STARTED", {
        "appointment_id": app.id,
        "dock_id": app.dock_id
    })
    return {"status": app.status}

@router.post("/{appointment_id}/complete-operation")
async def complete_operation(
    appointment_id: str,
    payload: Optional[GoodsReceiptSave] = None,
    db: AsyncSession = Depends(get_db)
):
    """Mal kabul tamamlandı, rampa serbest bırakıldı, SAP/U-ETDS fişi mühürlendi."""
    res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    app = res.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Yalnızca boşaltması devam eden araç tamamlanabilir
    if app.status != "UNLOADING":
        raise HTTPException(
            status_code=400,
            detail=f"İşlem Hatası: Yalnızca boşaltması devam eden (UNLOADING) araçların mal kabulü tamamlanabilir (Mevcut Statü: {app.status})."
        )

    app.status = "COMPLETED"
    app.actual_dock_out = datetime.now()

    # Free dock
    if app.dock_id:
        dock_res = await db.execute(select(Dock).where(Dock.id == app.dock_id))
        dock = dock_res.scalars().first()
        if dock:
            dock.status = "IDLE"

    # Save GoodsReceipt if items provided
    if payload:
        # Soğuk Zincir & Gıda Güvenliği (HACCP / ATP) Denetimi
        measured_temp = payload.measured_temperature_celsius
        is_cold = (app.load_type == "REEFER" or "soğuk" in (app.cargo_type or "").lower() or "süt" in (app.cargo_type or "").lower())
        sap_code = payload.sap_movement_code or "101"
        gr_status = "APPROVED"
        temp_status = "COMPLIANT"
        haccp_notes = payload.haccp_protocol_notes

        if is_cold:
            if measured_temp is None:
                # Kural: Soğuk zincirde sıcaklık ölçümü olmadan sağlam stok kabulü yapılamaz! (P0 Fix)
                temp_status = "MISSING_TEMP_BLOCKED"
                gr_status = "BLOCKED"
                sap_code = "103"  # SAP 103: Karantina / Bloke Mal Kabul
                app.cold_chain_status = "BREACH_REJECTED"
                haccp_notes = (
                    "HACCP KRİTİK GÜVENLİK İHLALİ: Frigo yük için sıcaklık ölçüm derecesi girilmedi! "
                    "ATP ve Gıda Güvenliği mevzuatı gereği ölçüm yapılmadan soğuk zincir kabulü yapılamaz. "
                    "Mal otomatik olarak SAP 103 ile karantinaya (Bloke Giriş) aktarıldı."
                )
            else:
                app.measured_temperature_celsius = measured_temp
                is_frozen = "dondur" in (app.cargo_type or "").lower()
                max_allowed = -15.0 if is_frozen else 4.0

                if measured_temp > max_allowed:
                    temp_status = "BREACH_BLOCKED"
                    gr_status = "BLOCKED"
                    sap_code = "103"  # SAP 103: Bloke Giriş / Karantina Hareketi
                    app.cold_chain_status = "BREACH_REJECTED"
                    haccp_notes = (
                        f"HACCP KRİTİK KONTROL NOKTASI (CCP-1) İHLALİ: Ölçülen sıcaklık ({measured_temp}°C) "
                        f"azami yasal limit olan {max_allowed}°C'yi aştı! Soğuk zincir kırıldığı için mal sağlam stoğa alınamaz. "
                        f"SAP 103 (Bloke Mal Kabul) fişi kesildi. Kalite Kontrol ve İade Raporu oluşturuldu."
                    )
                else:
                    app.cold_chain_status = "OPTIMAL"
                    temp_status = "COMPLIANT"
                    haccp_notes = f"Soğuk zincir ATP sertifikalı onaylandı: {measured_temp}°C (Set point limitinde)."

        gr = GoodsReceipt(
            appointment_id=app.id,
            waybill_number=payload.waybill_number or f"IRS-{app.id[:6].upper()}",
            e_waybill_uuid=payload.e_waybill_uuid or str(uuid.uuid4()),
            supplier_vkn=payload.supplier_vkn,
            supplier_title=payload.supplier_title,
            sap_movement_code=sap_code,
            uetds_reference_number=payload.uetds_reference_number or f"UETDS-{uuid.uuid4().hex[:8].upper()}",
            warehouse_notes=payload.warehouse_notes,
            measured_temperature_celsius=measured_temp,
            temperature_compliance_status=temp_status,
            haccp_protocol_notes=haccp_notes,
            status=gr_status
        )
        db.add(gr)
        await db.flush()

        for item in payload.items:
            db.add(GoodsReceiptItem(
                goods_receipt_id=gr.id,
                line_number=item.line_number,
                material_code=item.material_code,
                description=item.description,
                dispatched_qty=item.dispatched_qty,
                received_qty=item.received_qty,
                damaged_qty=item.damaged_qty,
                missing_qty=item.missing_qty,
                uom=item.uom,
                inspection_status=item.inspection_status
            ))

    db.add(GateLog(
        appointment_id=app.id,
        event_type="UNLOAD_END",
        notes="Boşaltma bitti. Çıkış izni verildi."
    ))
    await db.commit()

    await ws_hub.broadcast_event("DOCK_OPERATION_COMPLETED", {
        "appointment_id": app.id,
        "dock_id": app.dock_id
    })
    return {"message": "Mal kabul tamamlandı, rampa serbest.", "status": app.status}
