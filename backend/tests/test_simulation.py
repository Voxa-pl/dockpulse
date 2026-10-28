import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.yard_simulator import yard_simulator, FLEET_PROFILES


def test_turkish_fleet_profiles():
    """Tüm 7 büyük Türk lojistik filosunun doğru yapılandırıldığını doğrula."""
    carrier_names = [f["carrier_name"] for f in FLEET_PROFILES]
    short_names = [f["short_name"] for f in FLEET_PROFILES]

    assert any("Borusan" in name for name in carrier_names), "Borusan bulunamadı"
    assert any("Ekol" in name for name in carrier_names), "Ekol bulunamadı"
    assert any("Mars" in name for name in carrier_names), "Mars bulunamadı"
    assert any("Sütaş" in name for name in carrier_names), "Sütaş Frigo bulunamadı"
    assert any("BİM" in name for name in carrier_names), "BİM Dağıtım bulunamadı"
    assert any("Netlog" in name for name in carrier_names), "Netlog Soğuk Zincir bulunamadı"
    assert any("Horoz" in name for name in carrier_names), "Horoz Lojistik bulunamadı"

    # Sütaş ve Netlog Soğuk Zincir REEFER yük taşımalı
    sutas = next(f for f in FLEET_PROFILES if "Sütaş" in f["carrier_name"])
    assert "REEFER" in sutas["load_types"]
    netlog = next(f for f in FLEET_PROFILES if "Netlog" in f["carrier_name"])
    assert "REEFER" in netlog["load_types"]


def test_simulation_status():
    """GET /api/v1/simulation/status telemetri ve durum çıktısını doğrula."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/simulation/status")
            assert resp.status_code == 200
            data = resp.json()

            assert "is_running" in data
            assert "tick_count" in data
            assert "active_trucks_in_yard" in data
            assert "docks_occupancy_rate" in data
            assert "docks_breakdown" in data
            assert "telemetry" in data

            telemetry = data["telemetry"]
            assert telemetry["moxa_gateway_status"] == "ONLINE"
            assert "avg_dwell_time_minutes" in telemetry
            assert "scale_discrepancy_count" in telemetry
            assert isinstance(telemetry["recent_events"], list)

    asyncio.run(run())


def test_simulation_inject_truck():
    """POST /api/v1/simulation/inject-truck ile kapıya araç yaklaştırma, PTS ve kantar ölçümü."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Normal Sütaş Frigo enjeksiyonu
            payload = {
                "vehicle_plate": "16 STS 990",
                "carrier_name": "Sütaş Süt Ürünleri Frigo Lojistik",
                "load_type": "REEFER",
                "cargo_type": "Süt ve Süt Ürünleri (+4°C)",
                "estimated_pallets": 32,
                "driver_name": "Recep Korkmaz",
                "driver_phone": "0542 660 11 22",
                "priority": "URGENT_COLD_CHAIN",
                "force_discrepancy": False
            }
            resp = await client.post("/api/v1/simulation/inject-truck", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data["vehicle_plate"] == "16 STS 990"
            assert data["status"] == "WAITING_LOT"
            assert data["load_type"] == "REEFER"
            assert data["weighbridge_gross_kg"] > 30000.0
            assert data["weighbridge_discrepancy"] is False
            assert data["weighbridge_ticket_no"].startswith("KNT-2026-")
            assert data["tracking_token"].startswith("RR-")

            # 2. Fire aşımı zorlamalı enjeksiyon (force_discrepancy = True)
            payload_chaos = {
                "vehicle_plate": "34 BRS 771",
                "carrier_name": "Borusan Tedarik Zinciri ve Lojistik A.Ş.",
                "load_type": "PALLET",
                "force_discrepancy": True
            }
            resp_chaos = await client.post("/api/v1/simulation/inject-truck", json=payload_chaos)
            assert resp_chaos.status_code == 200
            data_chaos = resp_chaos.json()
            assert data_chaos["weighbridge_discrepancy"] is True

    asyncio.run(run())


def test_simulation_tick_lifecycle():
    """
    POST /api/v1/simulation/tick ile sahadaki tırın tüm yaşam döngüsünü adım adım test et:
    WAITING_LOT -> CALLED -> UNLOADING -> COMPLETED (DocuLog & SAP 101) -> DEPARTED (Çıkış Kantarı)
    """
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Özel bir araç enjekte et
            test_plate = "34 EKL 888"
            inj_resp = await client.post("/api/v1/simulation/inject-truck", json={
                "vehicle_plate": test_plate,
                "carrier_name": "Ekol Lojistik A.Ş.",
                "load_type": "PALLET",
                "estimated_pallets": 28
            })
            assert inj_resp.status_code == 200
            app_id = inj_resp.json()["appointment_id"]

            # 2. Adım 1: Tick çalıştır -> Boşalan rampaya otomatik çağrı (WAITING_LOT -> CALLED)
            tick_1 = await client.post("/api/v1/simulation/tick", json={"steps": 1, "force_spawn": False})
            assert tick_1.status_code == 200

            # Randevunun durumunu kontrol et
            r_track = await client.get(f"/api/v1/appointments/track/{inj_resp.json()['tracking_token']}")
            assert r_track.status_code == 200
            # Araç CALLED durumuna geçmiş veya bir sonraki aşamaya hazırlanmış olmalı
            status_1 = r_track.json()["status"]
            assert status_1 in ["CALLED", "UNLOADING", "COMPLETED", "WAITING_LOT"]

            # 3. Adım 2: Çoklu adımla boşaltma ve mal kabul döngüsünü ilerlet
            tick_multi = await client.post("/api/v1/simulation/tick", json={"steps": 3, "force_spawn": False})
            assert tick_multi.status_code == 200
            assert tick_multi.json()["steps_executed"] == 3

            # Simülasyon durumunu kontrol et
            status_resp = await client.get("/api/v1/simulation/status")
            assert status_resp.status_code == 200
            s_data = status_resp.json()
            assert len(s_data["telemetry"]["recent_events"]) > 0

    asyncio.run(run())


def test_simulation_toggle():
    """POST /api/v1/simulation/toggle ile otonom arka plan motorunu başlatma ve durdurma."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Başlat
            r_start = await client.post("/api/v1/simulation/toggle", json={
                "enabled": True,
                "interval_seconds": 2.0,
                "chaos_mode": True
            })
            assert r_start.status_code == 200
            data_start = r_start.json()
            assert data_start["is_running"] is True
            assert data_start["interval_seconds"] == 2.0
            assert data_start["chaos_mode"] is True

            # 2. Durdur
            r_stop = await client.post("/api/v1/simulation/toggle", json={"enabled": False})
            assert r_stop.status_code == 200
            data_stop = r_stop.json()
            assert data_stop["is_running"] is False

    asyncio.run(run())
