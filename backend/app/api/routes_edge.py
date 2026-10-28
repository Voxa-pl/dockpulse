"""
RampaRandevu Endüstriyel IoT ve Saha Donanım Entegrasyon API Rotası.
Endpoints:
- POST /api/v1/edge/anpr-event: Hikvision ve Dahua PTS kamera webhook alıcısı & otomatik bariyer tetikleme.
- POST /api/v1/edge/weighbridge: Baykon, Esit, Tunaylar kantar indikatörleri tartım & tolerans kontrolü.
- POST /api/v1/edge/barrier-pulse: Advantech ADAM-6060 Modbus TCP bariyer rölesi darbe kontrolü.
- GET  /api/v1/edge/status: Nizamiye donanımlarının canlı bağlantı ve sensör telemetrisi.
- POST /api/v1/edge/sync-offline-queue: Çevrimdışı (offline store-and-forward) kuyruk senkronizasyonu.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from datetime import datetime
from typing import Optional
import os
import uuid
import logging

from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.gate_log import GateLog
from app.schemas.edge import (
    ANPREventRequest,
    ANPREventResponse,
    WeighbridgeRequest,
    WeighbridgeResponse,
    BarrierPulseRequest,
    BarrierPulseResponse,
    EdgeStatusResponse,
    SyncOfflineQueueRequest,
    SyncOfflineQueueResponse
)
from app.services.ws_hub import ws_hub
from app.iot.anpr_parsers import ANPRParser, ParsedANPR
from app.iot.weighbridge_parsers import WeighbridgeParser, ParsedWeight, AxleComplianceResult
from app.iot.adam6060_modbus import adam6060, SafetyInterlockException
from app.iot.edge_gateway_sync import edge_store
from app.iot.telemetry_service import edge_telemetry

logger = logging.getLogger("dockpulse.api.edge")

# ============================================================================
# ENDÜSTRİYEL EDGE GÜVENLİK VE YETKİLENDİRME (P0 CRITICAL FIX)
# Nizamiye bariyeri, PTS ve kantar manipülasyonlarını engeller
# ============================================================================
EDGE_API_KEY = os.getenv("RAMPARANDEVU_EDGE_API_KEY", "DEV-RAMPA-EDGE-SECURE-KEY-2026")

async def verify_edge_auth(
    x_edge_api_key: Optional[str] = Header(None, alias="X-Edge-API-Key"),
    x_edge_token: Optional[str] = Header(None, alias="X-Edge-Token")
) -> str:
    token = x_edge_api_key or x_edge_token
    # Yalnızca konfigüre edilmiş kurumsal anahtar kabul edilir (Hardcoded bypass kaldırıldı)
    if not token or token != EDGE_API_KEY:
        logger.warning(f"Yetkisiz Edge donanım erişim girişimi engellendi! Token: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GÜVENLİK İHLALİ: Geçersiz veya eksik Edge Donanım Güvenlik Anahtarı (X-Edge-API-Key). Yetkisiz bariyer tetiklemesi ve kantar manipülasyonu engellendi."
        )
    return token

router = APIRouter(prefix="/edge", tags=["Industrial IoT & Edge Hardware"])

@router.post("/anpr-event", response_model=ANPREventResponse)
async def handle_anpr_event(
    req: ANPREventRequest,
    request: Request,
    _auth: str = Depends(verify_edge_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    PTS / ANPR Kameralarından (Hikvision ISAPI / Dahua TrafficCar / Generic Edge)
    gelen webhook verilerini karşılar, araç plakasını doğrular ve nizamiye giriş durumunu günceller.
    Yetkili randevu bulunursa ADAM-6060 rölesine otomatik bariyer açma darbesi gönderir.
    """
    # 1. Webhook Payload Çözümleme
    try:
        # Eğer raw body gönderilmişse
        body_bytes = await request.body()
        raw_text = body_bytes.decode("utf-8", errors="ignore") if body_bytes else None
        payload_to_parse = req.raw_payload or raw_text

        parsed: ParsedANPR = ANPRParser.parse(
            raw_payload=payload_to_parse if (payload_to_parse and len(payload_to_parse) > 10) else None,
            vendor_hint=req.vendor,
            direct_plate=req.plate_number,
            confidence=req.confidence,
            direction=req.direction,
            device_id=req.device_id
        )
    except Exception as e:
        logger.error(f"ANPR ayrıştırma hatası: {e}")
        raise HTTPException(status_code=400, detail=f"ANPR veri biçimi geçersiz: {str(e)}")

    plate_query = parsed.clean_plate
    formatted_plate = parsed.plate_number

    # Telemetri güncelle
    edge_telemetry.update_anpr_telemetry(parsed.camera_vendor, formatted_plate, parsed.direction)

    # Idempotency kontrolü
    if req.idempotency_key:
        existing_log = await db.execute(select(GateLog).where(GateLog.idempotency_key == req.idempotency_key))
        if existing_log.scalars().first():
            return ANPREventResponse(
                success=True,
                status="ALREADY_PROCESSED_IDEMPOTENT",
                detected_plate=formatted_plate,
                normalized_plate=plate_query,
                confidence=parsed.confidence,
                camera_vendor=parsed.camera_vendor,
                barrier_action="BARRIER_KEPT_CLOSED",
                relay_command_sent=False,
                message=f"Plaka {formatted_plate} için işlem daha önce işlendi (Idempotent)."
            )

    # 2. Veritabanında Aktif Randevu Arama
    res = await db.execute(
        select(Appointment).where(
            or_(
                func.replace(Appointment.vehicle_plate, " ", "") == plate_query,
                func.replace(Appointment.trailer_plate, " ", "") == plate_query,
                Appointment.vehicle_plate == formatted_plate
            )
        )
    )
    appointment = res.scalars().first()

    # 3. Eğer merkezi DB'de bulunamazsa yerel çevrimdışı beyaz listeyi sorgula
    offline_record = None
    if not appointment:
        offline_record = edge_store.check_offline_whitelist(plate_query)

    relay_sent = False
    barrier_action = "BARRIER_KEPT_CLOSED"

    # SENARYO A: Randevu Bulundu (Yetkili Araç)
    if appointment:
        old_status = appointment.status
        # Durumu güncelle (SCHEDULED -> WAITING_LOT)
        if appointment.status in ["SCHEDULED", "GATE_ARRIVED"]:
            appointment.status = "WAITING_LOT"
            appointment.actual_gate_in = datetime.now()
            status_desc = "VERIFIED_SCHEDULED"
        else:
            status_desc = f"ALREADY_IN_YARD_{appointment.status}"

        # Otomatik Bariyer Darbesi (ADAM-6060 DO0)
        if req.auto_open_barrier:
            try:
                pulse_res = await adam6060.pulse_barrier_open(
                    duration_ms=800,
                    operator=f"ANPR-{parsed.camera_vendor.upper()}",
                    reason=f"Yetkili Randevu: {formatted_plate} ({appointment.carrier_name})"
                )
                relay_sent = pulse_res.get("success", False)
                barrier_action = "BARRIER_PULSED"
            except Exception as e:
                logger.error(f"Bariyer röle tetikleme hatası: {e}")
                barrier_action = "BARRIER_MANUAL_REQUIRED"

        # GateLog oluştur
        gate_log = GateLog(
            appointment_id=appointment.id,
            event_type="GATE_IN_ANPR",
            gate_operator=req.operator or f"PTS-{parsed.camera_vendor.upper()}",
            idempotency_key=req.idempotency_key or f"ANPR-{uuid.uuid4().hex[:10]}",
            notes=f"PTS Kamera: {parsed.camera_vendor.upper()} ({parsed.device_id}). Güven: %{parsed.confidence}. Bariyer: {barrier_action}."
        )
        db.add(gate_log)
        await db.commit()

        # WebSocket Duyurusu
        await ws_hub.broadcast_event("VEHICLE_ARRIVED_AT_GATE", {
            "appointment_id": appointment.id,
            "vehicle_plate": appointment.vehicle_plate,
            "carrier_name": appointment.carrier_name,
            "status": appointment.status,
            "anpr_confidence": parsed.confidence,
            "barrier_opened": relay_sent
        })

        return ANPREventResponse(
            success=True,
            status=status_desc,
            detected_plate=formatted_plate,
            normalized_plate=plate_query,
            confidence=parsed.confidence,
            camera_vendor=parsed.camera_vendor,
            appointment_id=appointment.id,
            carrier_name=appointment.carrier_name,
            driver_name=appointment.driver_name,
            assigned_dock=appointment.dock_id,
            barrier_action=barrier_action,
            relay_command_sent=relay_sent,
            message=f"Araç onaylandı: {formatted_plate} ({appointment.carrier_name}). Bariyer açıldı -> Tır Parkı Bölge B."
        )

    # SENARYO B: Çevrimdışı Beyaz Liste ile Eşleşti (Offline Edge Match)
    elif offline_record:
        if req.auto_open_barrier:
            await adam6060.pulse_barrier_open(
                duration_ms=800,
                operator="EDGE_OFFLINE_WHITELIST",
                reason=f"Çevrimdışı Beyaz Liste: {formatted_plate}"
            )
            relay_sent = True
            barrier_action = "BARRIER_PULSED"

        # Store-and-Forward kuyruğuna yaz
        edge_store.enqueue_event("OFFLINE_ANPR_GATE_IN", {
            "plate_number": formatted_plate,
            "clean_plate": plate_query,
            "appointment_id": offline_record["appointment_id"],
            "timestamp": datetime.now().isoformat()
        }, req.idempotency_key)

        return ANPREventResponse(
            success=True,
            status="OFFLINE_AUTHORIZED",
            detected_plate=formatted_plate,
            normalized_plate=plate_query,
            confidence=parsed.confidence,
            camera_vendor=parsed.camera_vendor,
            appointment_id=offline_record["appointment_id"],
            carrier_name=offline_record.get("carrier_name"),
            driver_name=offline_record.get("driver_name"),
            barrier_action=barrier_action,
            relay_command_sent=relay_sent,
            message="Tesis çevrimdışı modda: Araç yerel randevu beyaz listesinden teyit edildi ve geçişe izin verildi."
        )

    # SENARYO C: Randevusuz / Tanımsız Araç
    else:
        # Yetkisiz geçiş denemesini logla
        unauth_log = GateLog(
            appointment_id=None,
            event_type="ANPR_UNMATCHED_PLATE",
            gate_operator=f"PTS-{parsed.camera_vendor.upper()}",
            idempotency_key=req.idempotency_key or f"ANPR-FAIL-{uuid.uuid4().hex[:10]}",
            notes=f"Randevusuz plaka algılandı: {formatted_plate}. Bariyer kapalı tutuldu. Operatör denetimi gerekli."
        )
        db.add(unauth_log)
        await db.commit()

        await ws_hub.broadcast_event("ANPR_UNAUTHORIZED_ALERT", {
            "vehicle_plate": formatted_plate,
            "confidence": parsed.confidence,
            "camera": parsed.device_id
        })

        return ANPREventResponse(
            success=False,
            status="NO_APPOINTMENT_FOUND",
            detected_plate=formatted_plate,
            normalized_plate=plate_query,
            confidence=parsed.confidence,
            camera_vendor=parsed.camera_vendor,
            barrier_action="BARRIER_KEPT_CLOSED",
            relay_command_sent=False,
            message=f"'{formatted_plate}' plakasına ait güncel randevu bulunamadı. Bariyer kapalı tutuldu."
        )

@router.post("/weighbridge", response_model=WeighbridgeResponse)
async def record_weighbridge_measurement(
    req: WeighbridgeRequest,
    _auth: str = Depends(verify_edge_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Kantar indikatörlerinden (Baykon, Esit, Tunaylar) gelen brüt veya dara tartım verilerini alır,
    net tonajı hesaplar, Karayolları / SAP tolerans kontrolü (±%3) ve KGM Md. 128 Aks Ağırlığı denetimi yapar.
    """
    # 1. Ağırlık Verisini Ayrıştır
    gross_val: float | None = None
    tare_val: float | None = None
    net_val: float | None = None
    is_stable = True
    vendor_name = (req.indicator_vendor or "generic").lower()
    parsed_w: Optional[ParsedWeight] = None

    if req.raw_ascii_data:
        try:
            parsed_w = WeighbridgeParser.parse_frame(req.raw_ascii_data, vendor_name)
            vendor_name = parsed_w.vendor
            is_stable = parsed_w.is_stable
            if parsed_w.weight_type == "GROSS":
                gross_val = parsed_w.weight_kg
            elif parsed_w.weight_type == "TARE":
                tare_val = parsed_w.weight_kg
            elif parsed_w.weight_type == "NET":
                net_val = parsed_w.weight_kg
            if parsed_w.gross_kg:
                gross_val = parsed_w.gross_kg
            if parsed_w.tare_kg:
                tare_val = parsed_w.tare_kg
            if parsed_w.net_kg:
                net_val = parsed_w.net_kg
        except Exception as e:
            logger.error(f"Kantar seri ASCII ayrıştırma hatası: {e}")
            raise HTTPException(status_code=400, detail=f"Kantar veri formatı geçersiz: {str(e)}")
    elif req.weight_kg is not None:
        if req.weighing_type in ["TARE", "SECOND_WEIGHING"]:
            tare_val = req.weight_kg
        else:
            gross_val = req.weight_kg
    else:
        raise HTTPException(status_code=400, detail="Tartım verisi (raw_ascii_data veya weight_kg) sağlanmalıdır.")

    # Aks Tartımı ve KGM Md. 128 Uyumluluk Denetimi
    steer_val = req.steer_axle_kg
    drive_val = req.drive_axle_kg
    trailer_val = req.trailer_tridem_kg
    axle_compliance: Optional[AxleComplianceResult] = None
    axle_overloaded = False
    axle_report = None
    rebalance_rec = None

    if parsed_w and parsed_w.axle_weights:
        steer_val = parsed_w.axle_weights.steer_axle_kg
        drive_val = parsed_w.axle_weights.drive_axle_kg
        trailer_val = parsed_w.axle_weights.trailer_axle_group_kg
        axle_compliance = parsed_w.axle_compliance
    elif steer_val is not None and drive_val is not None and trailer_val is not None:
        axle_compliance = WeighbridgeParser.calculate_axle_compliance(
            steer_kg=steer_val,
            drive_kg=drive_val,
            trailer_kg=trailer_val,
            total_gross_kg=gross_val
        )

    # Telemetri güncelle
    active_weight = gross_val or tare_val or net_val or 0.0
    edge_telemetry.update_weighbridge_telemetry(active_weight, is_stable, vendor_name)

    # 2. İlgili Randevuyu Bul
    appointment = None
    if req.appointment_id:
        res = await db.execute(select(Appointment).where(Appointment.id == req.appointment_id))
        appointment = res.scalars().first()
    elif req.plate_number:
        clean_plate = req.plate_number.replace(" ", "").upper()
        res = await db.execute(
            select(Appointment).where(
                or_(
                    func.replace(Appointment.vehicle_plate, " ", "") == clean_plate,
                    func.replace(Appointment.trailer_plate, " ", "") == clean_plate,
                    Appointment.vehicle_plate == req.plate_number.strip()
                )
            )
        )
        appointment = res.scalars().first()

    # Bilet Numarası
    ticket_no = req.ticket_number or f"KNT-2026-{uuid.uuid4().hex[:6].upper()}"

    # 3. Randevu Üzerinde Net Tonaj ve Tolerans Hesaplama
    within_tolerance = True
    discrepancy_pct = None
    warning_text = None

    if appointment:
        # Önceden kayıtlı brüt/dara varsa birleştir
        if gross_val is not None:
            appointment.weighbridge_gross_kg = gross_val
        elif appointment.weighbridge_gross_kg is not None:
            gross_val = appointment.weighbridge_gross_kg

        if tare_val is not None:
            appointment.weighbridge_tare_kg = tare_val
        elif appointment.weighbridge_tare_kg is not None:
            tare_val = appointment.weighbridge_tare_kg

        # Net tonajı hesapla
        if gross_val is not None and tare_val is not None:
            expected = req.expected_net_kg or appointment.weighbridge_net_kg
            calculated_net, within_tolerance, discrepancy_pct, warning_text = (
                WeighbridgeParser.calculate_net_and_tolerance(
                    gross_kg=gross_val,
                    tare_kg=tare_val,
                    expected_net_kg=expected
                )
            )
            appointment.weighbridge_net_kg = calculated_net
            appointment.weighbridge_discrepancy = not within_tolerance
            net_val = calculated_net

        appointment.weighbridge_ticket_no = ticket_no

        # GateLog kaydı
        log = GateLog(
            appointment_id=appointment.id,
            event_type="WEIGHBRIDGE_MEASUREMENT",
            gate_operator=req.operator or "Kantar-01",
            notes=f"Kantar {req.scale_id} ({vendor_name.upper()}): Brüt={gross_val} kg, Dara={tare_val} kg, Net={net_val} kg. Bilet: {ticket_no}."
        )
        db.add(log)
        await db.commit()

        # WebSocket Etkinliği
        await ws_hub.broadcast_event("WEIGHBRIDGE_MEASUREMENT_RECORDED", {
            "appointment_id": appointment.id,
            "vehicle_plate": appointment.vehicle_plate,
            "ticket_no": ticket_no,
            "gross_kg": gross_val,
            "tare_kg": tare_val,
            "net_kg": net_val,
            "within_tolerance": within_tolerance,
            "steer_axle_kg": steer_val,
            "drive_axle_kg": drive_val,
            "trailer_tridem_kg": trailer_val,
            "axle_overloaded": axle_overloaded
        })

    # Aks Aşımı Analiz ve Uyarı
    if axle_compliance:
        axle_overloaded = not axle_compliance.is_compliant
        if axle_compliance.violations:
            axle_report = " | ".join(axle_compliance.violations)
            rebalance_rec = axle_compliance.rebalance_recommendation
            if warning_text:
                warning_text = f"{warning_text} | {axle_report}"
            else:
                warning_text = axle_report

            await ws_hub.broadcast_event("AXLE_OVERLOAD_ALERT", {
                "plate_number": req.plate_number or (appointment.vehicle_plate if appointment else "UNKNOWN"),
                "drive_axle_kg": drive_val,
                "steer_axle_kg": steer_val,
                "trailer_tridem_kg": trailer_val,
                "drive_overload_kg": axle_compliance.drive_overload_kg,
                "rebalance_recommendation": rebalance_rec
            })

    return WeighbridgeResponse(
        success=True,
        appointment_id=appointment.id if appointment else None,
        vehicle_plate=appointment.vehicle_plate if appointment else req.plate_number,
        indicator_vendor=vendor_name,
        ticket_number=ticket_no,
        scale_id=req.scale_id or "SCALE-01",
        gross_kg=gross_val,
        tare_kg=tare_val,
        net_kg=net_val,
        is_stable=is_stable,
        unit="kg",
        weighing_type=req.weighing_type or "AUTO",
        within_tolerance=within_tolerance,
        discrepancy_percentage=discrepancy_pct,
        tolerance_limit_percent=WeighbridgeParser.DEFAULT_TOLERANCE_PERCENT,
        discrepancy_warning=warning_text,
        steer_axle_kg=steer_val,
        drive_axle_kg=drive_val,
        trailer_tridem_kg=trailer_val,
        axle_overloaded=axle_overloaded,
        axle_compliance_report=axle_report,
        rebalance_recommendation=rebalance_rec,
        message="Kantar tartım verisi başarıyla kaydedildi ve aks uyumluluğu doğrulandı."
    )

@router.post("/barrier-pulse", response_model=BarrierPulseResponse)
async def trigger_barrier_pulse(
    req: BarrierPulseRequest,
    _auth: str = Depends(verify_edge_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Advantech ADAM-6060 Modbus TCP röle sürücüsüne bariyer açma/kapama kontak darbesi gönderir.
    Fotosel ve manyetik loop sensör kilitlerini (Safety Interlock) denetler.
    """
    action_type = (req.action or "OPEN").upper()
    duration = req.pulse_duration_ms or 800

    try:
        if action_type == "OPEN":
            pulse_result = await adam6060.pulse_barrier_open(
                duration_ms=duration,
                operator=req.operator or "IoT-ADAM6060",
                reason=req.reason or "Bariyer Açma Pulse"
            )
        elif action_type == "CLOSE":
            pulse_result = await adam6060.pulse_barrier_close(
                duration_ms=duration,
                force_override=req.force_override or False
            )
        elif action_type == "EMERGENCY_OPEN":
            pulse_result = await adam6060.emergency_open(
                operator=req.operator or "PANIC_OVERRIDE"
            )
        else:
            raise HTTPException(status_code=400, detail=f"Desteklenmeyen eylem türü: {action_type}")

    except SafetyInterlockException as sie:
        logger.warning(f"Bariyer güvenlik kilidi engeli: {sie}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(sie)
        )
    except Exception as e:
        logger.error(f"ADAM-6060 Modbus darbe hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ADAM-6060 röle sürücüsü ile iletişim kurulamadı: {str(e)}"
        )

    # Saha Logu
    pulse_log = GateLog(
        appointment_id=None,
        event_type=f"BARRIER_{action_type}",
        gate_operator=req.operator or "ADAM-6060",
        notes=f"Geçiş Noktası: {req.gate_id}. Eylem: {action_type}. Süre: {duration}ms. Sebep: {req.reason}."
    )
    db.add(pulse_log)
    await db.commit()

    # WebSocket Duyurusu
    await ws_hub.broadcast_event("BARRIER_PULSE_TRIGGERED", {
        "gate_id": req.gate_id,
        "action": action_type,
        "duration_ms": duration,
        "operator": req.operator
    })

    return BarrierPulseResponse(
        success=pulse_result["success"],
        gate_id=req.gate_id or "GATE_01_IN",
        action=action_type,
        relay_channel=pulse_result["relay_channel"],
        pulse_duration_ms=duration,
        safety_photocell_clear=pulse_result["safety_photocell_clear"],
        loop_detector_active=pulse_result["loop_detector_active"],
        interlock_status=pulse_result["interlock_status"],
        message=pulse_result["message"]
    )

@router.get("/status", response_model=EdgeStatusResponse)
async def get_edge_status():
    """
    Nizamiye donanımlarının (PTS Kameraları, Kantar İndikatörü, ADAM-6060 Bariyer ve Loop Sensörleri)
    canlı bağlantı ve telemetri durumunu döndürür.
    """
    telemetry = await edge_telemetry.get_full_telemetry()
    return EdgeStatusResponse(**telemetry)

@router.post("/sync-offline-queue", response_model=SyncOfflineQueueResponse)
async def sync_offline_queue(
    req: SyncOfflineQueueRequest,
    _auth: str = Depends(verify_edge_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Tesis internet bağlantısı geri geldiğinde çevrimdışı store-and-forward
    kuyruğundaki olayları merkezi veritabanına aktarır.
    """
    pending = edge_store.get_pending_events(limit=req.limit or 50)
    synced_count = 0
    failed_count = 0
    errors = []

    for item in pending:
        try:
            # Idempotency kontrolü
            idem_key = item["idempotency_key"]
            existing = await db.execute(select(GateLog).where(GateLog.idempotency_key == idem_key))
            if not existing.scalars().first():
                payload = item["payload"]
                app_id = payload.get("appointment_id")
                if app_id:
                    app_res = await db.execute(select(Appointment).where(Appointment.id == app_id))
                    target_app = app_res.scalars().first()
                    if target_app and (item["event_type"] in ("ANPR_ENTRY", "GATE_IN", "GATE_OVERRIDE", "OFFLINE_ANPR_GATE_IN", "OFFLINE_ENTRY") or "GATE_IN" in item["event_type"]):
                        target_app.status = "WAITING_LOT"
                        if not target_app.actual_gate_in:
                            try:
                                target_app.actual_gate_in = datetime.fromisoformat(item["created_at"])
                            except Exception:
                                target_app.actual_gate_in = datetime.now()

                log = GateLog(
                    appointment_id=app_id,
                    event_type=f"OFFLINE_SYNC_{item['event_type']}",
                    gate_operator="STORE_AND_FORWARD_SYNC",
                    idempotency_key=idem_key,
                    notes=f"Çevrimdışı kuyruktan aktarıldı. Orijinal zaman: {item['created_at']}"
                )
                db.add(log)
                await db.commit()

                if app_id:
                    await ws_hub.broadcast_event("VEHICLE_ARRIVED_GATE", {
                        "appointment_id": app_id,
                        "status": "WAITING_LOT",
                        "source": "EDGE_STORE_AND_FORWARD_SYNC"
                    })
            edge_store.mark_event_synced(item["id"])
            synced_count += 1
        except Exception as e:
            failed_count += 1
            err_msg = f"Olay {item['id']} senkronize edilemedi: {str(e)}"
            errors.append(err_msg)
            edge_store.mark_event_failed(item["id"], err_msg)

    metrics = edge_store.get_queue_metrics()
    return SyncOfflineQueueResponse(
        processed_count=len(pending),
        synced_count=synced_count,
        failed_count=failed_count,
        remaining_pending=metrics["pending_events"],
        errors=errors
    )
