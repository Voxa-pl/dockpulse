from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.schemas.simulation import (
    SimulationTickRequest,
    SimulationToggleRequest,
    TruckInjectionRequest
)
from app.services.yard_simulator import yard_simulator

router = APIRouter(prefix="/simulation", tags=["Autonomous Yard Simulation"])

@router.post("/tick")
async def simulation_tick(
    req: Optional[SimulationTickRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Simülasyon motorunu bir veya birkaç adım manuel olarak ilerletir.
    - PTS Plaka Okuma ve Kantar Tartımı
    - Boşalan rampalara tampon parktan akıllı çağrı
    - Rampa körüğüne yanaşma ve DocuLog AI sayımı
    - Çıkış kantarı ve nizamiye sefer kapanışı
    """
    steps = max(1, min(req.steps if req and req.steps else 1, 10))
    force_spawn = req.force_spawn if req else False

    last_result = None
    all_events = []

    for step_idx in range(steps):
        spawn_this_step = force_spawn and (step_idx == 0)
        res = await yard_simulator.tick(db, force_spawn=spawn_this_step)
        all_events.extend(res.get("events", []))
        last_result = res

    await db.commit()

    return {
        "status": "success",
        "steps_executed": steps,
        "tick": yard_simulator.tick_count,
        "timestamp": yard_simulator.last_tick_at.isoformat() if yard_simulator.last_tick_at else None,
        "total_events": len(all_events),
        "events": all_events,
        "summary": last_result.get("summary") if last_result else {}
    }

@router.post("/toggle")
async def simulation_toggle(
    req: Optional[SimulationToggleRequest] = Body(default=None)
):
    """
    Otonom arka plan simülasyonunu başlatır veya durdurur.
    Simülasyon hızı (interval_seconds), kaos modu ve otomatik araç akışı parametrelerini günceller.
    """
    enabled = req.enabled if req else None
    interval = req.interval_seconds if req else None
    chaos = req.chaos_mode if req else None
    auto_spawn = req.auto_spawn if req else None

    result = yard_simulator.toggle(
        enabled=enabled,
        interval_seconds=interval,
        chaos_mode=chaos,
        auto_spawn=auto_spawn
    )

    action_msg = (
        "Otonom 7/24 saha simülasyonu BAŞLATILDI."
        if result["is_running"]
        else "Otonom saha simülasyonu DURDURULDU."
    )

    return {
        "message": action_msg,
        **result
    }

@router.post("/inject-truck")
async def simulation_inject_truck(
    req: TruckInjectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    İstenen plaka, taşıyıcı ve yük tipiyle anında nizamiye kapısına tır gönderir.
    Araç doğrudan PTS kamerasından geçer, giriş kantarında brüt tartılır ve tampon parka alınır.
    """
    app = await yard_simulator.inject_truck(
        db=db,
        vehicle_plate=req.vehicle_plate,
        carrier_name=req.carrier_name,
        load_type=req.load_type,
        cargo_type=req.cargo_type,
        estimated_pallets=req.estimated_pallets,
        driver_name=req.driver_name,
        driver_phone=req.driver_phone,
        priority=req.priority,
        force_discrepancy=req.force_discrepancy
    )
    await db.commit()

    return {
        "message": f"{app.vehicle_plate} tırı nizamiye kapısına başarıyla yanaştırıldı.",
        "appointment_id": app.id,
        "vehicle_plate": app.vehicle_plate,
        "trailer_plate": app.trailer_plate,
        "carrier_name": app.carrier_name,
        "load_type": app.load_type,
        "cargo_type": app.cargo_type,
        "estimated_pallets": app.estimated_pallets,
        "status": app.status,
        "weighbridge_ticket_no": app.weighbridge_ticket_no,
        "weighbridge_gross_kg": app.weighbridge_gross_kg,
        "weighbridge_discrepancy": app.weighbridge_discrepancy,
        "tracking_token": app.tracking_token,
        "driver_name": app.driver_name,
        "driver_phone": app.driver_phone
    }

@router.get("/status")
async def simulation_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Simülasyon durumunu ve canlı saha IoT telemetrisini döner.
    - ANPR kamera, aks kantarı ve Moxa Gateway telemetrileri
    - Rampa doluluk oranları, tampon park ve bekleme süreleri
    - Son 50 saha olayı günlüğü
    """
    status_data = await yard_simulator.get_status(db)
    return status_data
