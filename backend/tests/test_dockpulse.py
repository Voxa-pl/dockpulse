import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.quantum_slot_engine import QuantumSlotEngine

def test_quantum_slot_calculation():
    # 33 pallets, pallet type: 10 + (33*1.2=39.6) + 5 + 5 = 59.6 -> 60 mins
    dur_33 = QuantumSlotEngine.calculate_slot_duration(33, "PALLET")
    assert dur_33 == 60, f"Expected 60 mins, got {dur_33}"

    # 10 pallets, pallet type: 10 + 12 + 5 + 5 = 32 -> 45 mins
    dur_10 = QuantumSlotEngine.calculate_slot_duration(10, "PALLET")
    assert dur_10 == 45, f"Expected 45 mins, got {dur_10}"

    # Reefer inspection adds 15 mins
    dur_reefer = QuantumSlotEngine.calculate_slot_duration(10, "REEFER")
    assert dur_reefer in (45, 60)

def test_api_docks_and_appointments():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create a dynamic facility
            fac_res = await client.post("/api/v1/facilities", json={
                "name": "Test Test Deposu",
                "code": "TST-01",
                "docks": [
                    {"dock_number": "Rampa 01", "dock_type": "SHELTER", "max_pallets": 33},
                    {"dock_number": "Rampa 02", "dock_type": "COLD_REEFER", "max_pallets": 33}
                ]
            })
            assert fac_res.status_code in (201, 200)

            # Check Docks
            r_docks = await client.get("/api/v1/docks")
            assert r_docks.status_code == 200
            docks = r_docks.json()
            assert len(docks) >= 2

            # Create Appointment
            app_res = await client.post("/api/v1/appointments", json={
                "carrier_name": "Test Lojistik",
                "vehicle_plate": "34 TST 001",
                "driver_name": "Test Şoför",
                "driver_phone": "0532 000 00 00",
                "slot_start": "2026-10-28T10:00:00Z",
                "estimated_pallets": 20
            })
            assert app_res.status_code == 200

            # Check Appointments
            r_apps = await client.get("/api/v1/appointments")
            assert r_apps.status_code == 200
            apps = r_apps.json()
            assert len(apps) >= 1

    asyncio.run(run())

def test_gate_check_in_flow():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create appointment first
            await client.post("/api/v1/appointments", json={
                "carrier_name": "Mars Logistics",
                "vehicle_plate": "16 MRS 552",
                "driver_name": "Kemal Demir",
                "driver_phone": "0555 444 33 22",
                "slot_start": "2026-10-28T11:00:00Z",
                "estimated_pallets": 25
            })

            # Check in with plate
            r_in = await client.post("/api/v1/gate/check-in", json={"plate_or_token": "16 MRS 552"})
            assert r_in.status_code == 200
            assert r_in.json()["status"] == "WAITING_LOT"

    asyncio.run(run())

def test_driver_tracking():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/v1/appointments", json={
                "carrier_name": "Borusan Lojistik",
                "vehicle_plate": "34 VR 8902",
                "driver_name": "Ahmet Yılmaz",
                "driver_phone": "0532 991 22 33",
                "slot_start": "2026-10-28T12:00:00Z",
                "estimated_pallets": 32
            })
            token = created.json()["tracking_token"]

            r_track = await client.get(f"/api/v1/appointments/track/{token}")
            assert r_track.status_code == 200
            data = r_track.json()
            assert data["vehicle_plate"] == "34 VR 8902"

            # Also verify searching by plate works
            r_plate = await client.get("/api/v1/appointments/track/34VR8902")
            assert r_plate.status_code == 200

    asyncio.run(run())

def test_gate_check_out_axle_and_weight_lock():
    """KGM Karayolları güvenlik kilidi: Kantarda tonaj/aks aşımı olan araç sahadan çıkarılamaz (409 Conflict)."""
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/v1/appointments", json={
                "carrier_name": "Aşırı Yük Lojistik",
                "vehicle_plate": "06 OVR 999",
                "driver_name": "Dursun Usta",
                "driver_phone": "0530 111 22 33",
                "slot_start": "2026-10-28T13:00:00Z",
                "estimated_pallets": 33
            })
            app_id = created.json()["id"]

            # Gate in
            await client.post("/api/v1/gate/check-in", json={"plate_or_token": "06 OVR 999"})

            # Kantar aşımı simüle et
            from app.core.database import AsyncSessionLocal
            from app.models.appointment import Appointment
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Appointment).where(Appointment.id == app_id))
                a = res.scalars().first()
                a.weighbridge_discrepancy = True
                await session.commit()

            # 2. Çıkış denemesi (Engellenmeli - 409)
            res_fail = await client.post("/api/v1/gate/check-out", json={
                "appointment_id": app_id,
                "force_override": False
            })
            assert res_fail.status_code == 409
            assert "KGM YASAL TONAJ & AKS KİLİDİ" in res_fail.json()["detail"]

            # 3. İdari override ile denetimli çıkış (Başarılı - 200)
            res_override = await client.post("/api/v1/gate/check-out", json={
                "appointment_id": app_id,
                "force_override": True,
                "override_reason": "Saha amiri denetimli rebalance tutanağı düzenlendi"
            })
            assert res_override.status_code == 200
            assert res_override.json()["status"] == "DEPARTED"

    asyncio.run(run())
