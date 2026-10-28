"""
RampaRandevu Endüstriyel IoT & Saha Donanım Entegrasyon Testleri.
Test Kapsamı:
1. Hikvision ve Dahua PTS Kamera Webhook Ayrıştırıcıları
2. Baykon, Esit, Tunaylar Kantar RS232/RS485 ASCII Ayrıştırıcıları ve Tolerans Hesaplama
3. Advantech ADAM-6060 Modbus TCP Röle Sürücüsü ve Güvenlik Kilidi (Safety Interlock)
4. Çevrimdışı (Offline Store-and-Forward) Edge Gateway Kuyruğu ve Yerel Beyaz Liste
5. FastAPI /api/v1/edge Endpoints (ANPR, Kantar, Bariyer, Telemetri, Kuyruk Senkronizasyonu)
"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.iot.anpr_parsers import ANPRParser
from app.iot.weighbridge_parsers import WeighbridgeParser
from app.iot.adam6060_modbus import adam6060, SafetyInterlockException
from app.iot.edge_gateway_sync import EdgeStoreAndForward
from app.iot.telemetry_service import edge_telemetry

# ----------------- 1. PTS / ANPR Webhook Ayrıştırma Testleri -----------------

def test_anpr_parser_hikvision_xml():
    """Hikvision ISAPI XML bildiriminin doğru ayrıştırıldığını test eder."""
    sample_hik_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <EventNotificationAlert version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <ipAddress>192.168.1.101</ipAddress>
        <portNo>80</portNo>
        <channelID>1</channelID>
        <dateTime>2026-10-27T10:15:30+03:00</dateTime>
        <eventType>ANPR</eventType>
        <ANPR>
            <licensePlate>34 VR 8902</licensePlate>
            <confidenceLevel>98.7</confidenceLevel>
            <direction>in</direction>
            <vehicleType>TRUCK</vehicleType>
        </ANPR>
    </EventNotificationAlert>
    """
    parsed = ANPRParser.parse(raw_payload=sample_hik_xml, vendor_hint="hikvision")
    assert parsed.plate_number == "34 VR 8902"
    assert parsed.clean_plate == "34VR8902"
    assert parsed.confidence == 98.7
    assert parsed.direction == "ENTRY"
    assert parsed.camera_vendor == "hikvision"
    assert parsed.vehicle_type == "TRUCK"

def test_anpr_parser_dahua_json():
    """Dahua TrafficCar JSON bildiriminin doğru ayrıştırıldığını test eder."""
    sample_dahua_json = """{
        "Events": [
            {
                "Code": "TrafficCar",
                "Data": {
                    "PlateNumber": "41 ABC 710",
                    "Confidence": 96.2,
                    "Direction": "0",
                    "VehicleType": "HeavyTruck",
                    "VehicleColor": "Blue",
                    "Lane": 1
                },
                "UTC": 1729864200
            }
        ],
        "DeviceAddress": "192.168.1.102"
    }"""
    parsed = ANPRParser.parse(raw_payload=sample_dahua_json, vendor_hint="dahua")
    assert parsed.plate_number == "41 ABC 710"
    assert parsed.clean_plate == "41ABC710"
    assert parsed.confidence == 96.2
    assert parsed.direction == "ENTRY"
    assert parsed.camera_vendor == "dahua"
    assert parsed.vehicle_type == "HeavyTruck"

def test_anpr_plate_normalization():
    """Türkiye plaka formatlama ve temizleme kurallarını test eder."""
    cases = [
        (" 34-vr-8902 ", "34 VR 8902", "34VR8902"),
        ("16.mrs.552", "16 MRS 552", "16MRS552"),
        ("06oz199", "06 OZ 199", "06OZ199"),
        ("35 STZ 404", "35 STZ 404", "35STZ404"),
        ("34-BİM-091", "34 BİM 091", "34BİM091"),
    ]
    for raw, exp_fmt, exp_compact in cases:
        fmt, compact = ANPRParser.normalize_plate(raw)
        assert fmt == exp_fmt, f"Format failed for '{raw}': got '{fmt}', expected '{exp_fmt}'"
        assert compact == exp_compact, f"Compact failed for '{raw}': got '{compact}', expected '{exp_compact}'"

# ----------------- 2. Kantar ASCII Ayrıştırma & Tolerans Testleri -----------------

def test_weighbridge_baykon_parser():
    """Baykon BX serisi multi-field ve sürekli akış formatlarını test eder."""
    # Format A: WB / WD / WN
    baykon_multi = "WB: 41240 kg  WD: 16820 kg  WN: 24420 kg\r\n"
    res_multi = WeighbridgeParser.parse_frame(baykon_multi, vendor_hint="baykon")
    assert res_multi.vendor == "baykon"
    assert res_multi.gross_kg == 41240.0
    assert res_multi.tare_kg == 16820.0
    assert res_multi.net_kg == 24420.0
    assert res_multi.is_stable is True

    # Format B: Sürekli akış
    baykon_cont = "\x02+041240 kg G\r\n"
    res_cont = WeighbridgeParser.parse_frame(baykon_cont, vendor_hint="baykon")
    assert res_cont.weight_kg == 41240.0
    assert res_cont.weight_type == "GROSS"
    assert res_cont.is_stable is True

def test_weighbridge_esit_parser():
    """Esit ART serisi ASCII çerçevelerini (Brüt B, Dara T) test eder."""
    # Brüt
    esit_gross = "\x02B+041240kg\r"
    res_g = WeighbridgeParser.parse_frame(esit_gross, vendor_hint="esit")
    assert res_g.vendor == "esit"
    assert res_g.weight_kg == 41240.0
    assert res_g.weight_type == "GROSS"
    assert res_g.gross_kg == 41240.0

    # Dara
    esit_tare = "\x02T+016820kg\r"
    res_t = WeighbridgeParser.parse_frame(esit_tare, vendor_hint="esit")
    assert res_t.weight_kg == 16820.0
    assert res_t.weight_type == "TARE"
    assert res_t.tare_kg == 16820.0

def test_weighbridge_tunaylar_parser():
    """Tunaylar LPi serisi ASCII akışlarını test eder."""
    tunaylar_str = "BRUT: 41240 kg\r\n"
    res = WeighbridgeParser.parse_frame(tunaylar_str, vendor_hint="tunaylar")
    assert res.vendor == "tunaylar"
    assert res.gross_kg == 41240.0
    assert res.weight_type == "GROSS"

def test_weighbridge_tolerance_calculations():
    """Yasal tolerans kontrolü ve azami katar ağırlık uyarısını test eder."""
    # 1. Tolerans dahilinde (%1.7 sapma <= %3)
    net, within_tol, dev_pct, warn = WeighbridgeParser.calculate_net_and_tolerance(
        gross_kg=41240.0,
        tare_kg=16820.0,
        expected_net_kg=24000.0,  # Fark: 420 kg, Sapma: %1.75
        tolerance_pct=3.0
    )
    assert net == 24420.0
    assert within_tol is True
    assert dev_pct == 1.75

    # 2. Tolerans aşımı (%8.3 sapma > %3)
    net2, within_tol2, dev_pct2, warn2 = WeighbridgeParser.calculate_net_and_tolerance(
        gross_kg=41240.0,
        tare_kg=16820.0,
        expected_net_kg=22500.0,  # Fark: 1920 kg, Sapma: %8.53
        tolerance_pct=3.0
    )
    assert within_tol2 is False
    assert dev_pct2 > 3.0
    assert "saptı" in warn2

# ----------------- 3. ADAM-6060 Modbus TCP & Güvenlik Kilidi Testleri -----------------

def test_adam6060_modbus_pulse_open():
    """ADAM-6060 bariyer açma darbesini ve trafik ışıklarını test eder."""
    async def run():
        # Ön koşul: Güvenlik fotoseli temiz
        adam6060.simulate_hardware_event(loop_active=True, photocell_clear=True, barrier_open=False)
        
        res = await adam6060.pulse_barrier_open(duration_ms=100, operator="TEST_SUITE")
        assert res["success"] is True
        assert res["relay_channel"] == 0
        assert res["action"] == "OPEN"

        # Çıkışlar: Darbe bitti, yeşil ışık yandı
        coils = await adam6060.read_coils()
        assert coils["traffic_light_green"] is True
        assert coils["traffic_light_red"] is False
    asyncio.run(run())

def test_adam6060_safety_interlock_blocks_close():
    """Bariyer altında araç varken (Güvenlik fotoseli kesilmişken) kapatmanın engellendiğini test eder."""
    async def run():
        # Bariyer açık, fakat altındaki fotosel ışını kesilmiş (photocell_clear=False)
        adam6060.simulate_hardware_event(loop_active=False, photocell_clear=False, barrier_open=True)

        # Kapatma denemesi SafetyInterlockException fırlatmalı
        with pytest.raises(SafetyInterlockException) as exc_info:
            await adam6060.pulse_barrier_close(duration_ms=100)
        assert "GÜVENLİK ENGELİ" in str(exc_info.value)

        # Fotosel temizlendiğinde kapatma başarılı olmalı
        adam6060.simulate_hardware_event(photocell_clear=True, loop_active=False)
        close_res = await adam6060.pulse_barrier_close(duration_ms=100)
        assert close_res["success"] is True
        assert close_res["action"] == "CLOSE"

        # Kırmızı ışık aktif olmalı
        coils = await adam6060.read_coils()
        assert coils["traffic_light_red"] is True
        assert coils["traffic_light_green"] is False
    asyncio.run(run())

def test_adam6060_emergency_open():
    """Acil durum komutunda bariyerin açık konuma kilitlenip sirenin çaldığını test eder."""
    async def run():
        res = await adam6060.emergency_open(operator="ITFAİYE_OVERRIDE")
        assert res["success"] is True
        assert res["interlock_status"] == "OVERRIDDEN"

        coils = await adam6060.read_coils()
        assert coils["barrier_open_relay"] is True
        assert coils["siren_active"] is True
        assert coils["traffic_light_green"] is True

        # Test sonrası temizle
        adam6060.state.do[4] = False
    asyncio.run(run())

# ----------------- 4. Çevrimdışı (Store-and-Forward) Edge Gateway Testleri -----------------

def test_edge_store_and_forward_queue(tmp_path):
    """Tesis interneti koptuğunda yerel SQLite kuyruğunun çalıştığını test eder."""
    db_file = str(tmp_path / "test_edge_queue.db")
    edge_sync = EdgeStoreAndForward(db_path=db_file)

    # 1. Olay ekle
    idem_key = edge_sync.enqueue_event(
        event_type="OFFLINE_ANPR_EVENT",
        payload={"plate": "34 VR 8902", "confidence": 98.5}
    )
    assert idem_key is not None

    # 2. Bekleyenleri getir
    pending = edge_sync.get_pending_events()
    assert len(pending) == 1
    assert pending[0]["event_type"] == "OFFLINE_ANPR_EVENT"
    assert pending[0]["payload"]["plate"] == "34 VR 8902"

    # 3. Senkronize et
    edge_sync.mark_event_synced(pending[0]["id"])
    pending_after = edge_sync.get_pending_events()
    assert len(pending_after) == 0

    # 4. Beyaz liste önbellekleme
    edge_sync.cache_whitelist([
        {"id": "APP-01", "vehicle_plate": "34 VR 8902", "carrier_name": "Borusan"}
    ])
    matched = edge_sync.check_offline_whitelist("34VR8902")
    assert matched is not None
    assert matched["carrier_name"] == "Borusan"

# ----------------- 5. FastAPI /api/v1/edge Entegrasyon Testleri -----------------

EDGE_HEADERS = {"X-Edge-API-Key": "DEV-RAMPA-EDGE-SECURE-KEY-2026"}

def test_api_edge_security_unauthorized():
    """Güvenlik denetimi: API key olmadan bariyer veya kantar çağrısı 401 Unauthorized almalıdır."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. API Keysiz bariyer darbesi denemesi
            res_pulse = await client.post("/api/v1/edge/barrier-pulse", json={
                "gate_id": "GATE_01_IN",
                "action": "OPEN"
            })
            assert res_pulse.status_code == 401
            assert "GÜVENLİK İHLALİ" in res_pulse.json()["detail"]

            # 2. Sahte API Key ile deneme
            res_fake = await client.post(
                "/api/v1/edge/barrier-pulse",
                headers={"X-Edge-API-Key": "HACKER_ATTEMPT"},
                json={"gate_id": "GATE_01_IN", "action": "OPEN"}
            )
            assert res_fake.status_code == 401

            # 3. API Keysiz kantar verisi denemesi
            res_weigh = await client.post("/api/v1/edge/weighbridge", json={"weight_kg": 24000.0})
            assert res_weigh.status_code == 401
    asyncio.run(run())

def test_axle_compliance_drive_overload():
    """KGM Md. 128: Toplam ağırlık yasal olsa bile çeker aksın 11.5t aşması tespit edilmelidir."""
    # Toplam: 38.000 kg (40 ton yasal sınır altında)
    # Ön aks: 6.200 kg (10t altı)
    # Çeker aks: 12.800 kg (11.5t limitini 1.300 kg aşıyor!)
    # Römork: 19.000 kg (24t altı)
    res = WeighbridgeParser.calculate_axle_compliance(
        steer_kg=6200.0,
        drive_kg=12800.0,
        trailer_kg=19000.0,
        total_gross_kg=38000.0
    )
    assert res.is_compliant is False
    assert res.drive_overload_kg == 1300.0
    assert res.steer_overload_kg == 0.0
    assert res.total_overload_kg == 0.0
    assert len(res.violations) == 1
    assert "Çeker tahrik dingili" in res.violations[0]
    assert "Weight Re-distribution" in res.rebalance_recommendation

def test_axle_ascii_parsing():
    """Baykon/Tunaylar çoklu aks kantar ASCII çerçevesinin ayrıştırılması."""
    axle_frame = "AXLES: 6200, 11200, 21500\r\n"
    parsed = WeighbridgeParser.parse_frame(axle_frame, vendor_hint="baykon")
    assert parsed.axle_weights is not None
    assert parsed.axle_weights.steer_axle_kg == 6200.0
    assert parsed.axle_weights.drive_axle_kg == 11200.0
    assert parsed.axle_weights.trailer_axle_group_kg == 21500.0
    assert parsed.axle_compliance.is_compliant is True

def test_api_anpr_event_authorized():
    """PTS webhook: Randevulu araç için doğrulama ve otomatik bariyer açılışı."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Önce randevuyu dinamik olarak oluştur
            await client.post("/api/v1/appointments", json={
                "carrier_name": "BİM Dağıtım",
                "vehicle_plate": "34 BIM 091",
                "driver_name": "Salih Kurt",
                "driver_phone": "0532 999 88 77",
                "slot_start": "2026-10-28T09:00:00Z",
                "estimated_pallets": 30
            })

            payload = {
                "vendor": "hikvision",
                "device_id": "CAM-GATE-IN-01",
                "plate_number": "34 BIM 091",
                "confidence": 98.4,
                "direction": "ENTRY",
                "auto_open_barrier": True
            }
            res = await client.post("/api/v1/edge/anpr-event", headers=EDGE_HEADERS, json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["detected_plate"] == "34 BIM 091"
            assert data["normalized_plate"] == "34BIM091"
            assert data["barrier_action"] == "BARRIER_PULSED"
            assert data["relay_command_sent"] is True
            assert "Bariyer açıldı" in data["message"]
    asyncio.run(run())

def test_api_anpr_event_unauthorized():
    """PTS webhook: Randevusuz araçta bariyerin kapalı tutulması."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "vendor": "dahua",
                "plate_number": "34 BILINMEYEN 99",
                "confidence": 94.0,
                "direction": "ENTRY",
                "auto_open_barrier": True
            }
            res = await client.post("/api/v1/edge/anpr-event", headers=EDGE_HEADERS, json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is False
            assert data["status"] == "NO_APPOINTMENT_FOUND"
            assert data["barrier_action"] == "BARRIER_KEPT_CLOSED"
            assert data["relay_command_sent"] is False
    asyncio.run(run())

def test_api_weighbridge_measurement():
    """Kantar tartım endpointi: Brüt ve dara ile net tonaj & tolerans hesaplama."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 34 VR 8902 aracı için Baykon kantar verisi
            payload = {
                "indicator_vendor": "baykon",
                "raw_ascii_data": "WB: 39800 kg  WD: 15400 kg  WN: 24400 kg\r\n",
                "plate_number": "34 VR 8902",
                "scale_id": "KANTAR-01-GIRIS",
                "expected_net_kg": 24400.0,
                "steer_axle_kg": 5800.0,
                "drive_axle_kg": 11200.0,
                "trailer_tridem_kg": 22800.0
            }
            res = await client.post("/api/v1/edge/weighbridge", headers=EDGE_HEADERS, json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["gross_kg"] == 39800.0
            assert data["tare_kg"] == 15400.0
            assert data["net_kg"] == 24400.0
            assert data["within_tolerance"] is True
            assert data["axle_overloaded"] is False
            assert data["ticket_number"].startswith("KNT-2026-")
    asyncio.run(run())

def test_api_barrier_pulse_open_and_safety_interlock():
    """Bariyer röle tetikleme ve güvenlik fotoseli kilidi HTTP testi."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Açma darbesi (Başarılı)
            adam6060.simulate_hardware_event(photocell_clear=True, loop_active=False)
            res_open = await client.post("/api/v1/edge/barrier-pulse", headers=EDGE_HEADERS, json={
                "gate_id": "GATE_01_IN",
                "action": "OPEN",
                "pulse_duration_ms": 100,
                "reason": "Test Açma"
            })
            assert res_open.status_code == 200
            assert res_open.json()["success"] is True
            assert res_open.json()["relay_channel"] == 0

            # 2. Güvenlik fotoseli engelliyken kapatma denemesi (409 Conflict)
            adam6060.simulate_hardware_event(photocell_clear=False)
            res_close_fail = await client.post("/api/v1/edge/barrier-pulse", headers=EDGE_HEADERS, json={
                "gate_id": "GATE_01_IN",
                "action": "CLOSE",
                "pulse_duration_ms": 100
            })
            assert res_close_fail.status_code == 409
            assert "GÜVENLİK ENGELİ" in res_close_fail.json()["detail"]
    asyncio.run(run())

def test_api_edge_status_telemetry():
    """Nizamiye donanımlarının canlı telemetri endpointi."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/edge/status")
            assert res.status_code == 200
            data = res.json()
            assert "gateway_id" in data
            assert data["overall_status"] in ["ONLINE", "WARNING (PHOTOCELL_OBSTRUCTED)", "DEGRADED (OFFLINE_EDGE_MODE)"]
            assert "cameras" in data
            assert "hikvision_inbound_anpr" in data["cameras"]
            assert "weighbridge" in data
            assert "barrier_controller" in data
            assert "magnetic_loops" in data
            assert "system_metrics" in data
            assert "offline_store_and_forward" in data
    asyncio.run(run())

def test_api_sync_offline_queue():
    """Kuyruk senkronizasyon endpointi."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/edge/sync-offline-queue", headers=EDGE_HEADERS, json={"limit": 50})
            assert res.status_code == 200
            data = res.json()
            assert "processed_count" in data
            assert "synced_count" in data
    asyncio.run(run())
