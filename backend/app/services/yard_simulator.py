import asyncio
import collections
from datetime import datetime, timedelta
import logging
import math
import random
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select, case, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment
from app.models.dock import Dock
from app.models.gate_log import GateLog
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptItem
from app.models.facility import Facility
from app.services.quantum_slot_engine import QuantumSlotEngine
from app.services.ws_hub import ws_hub

logger = logging.getLogger("yard_simulator")

# ============================================================================
# GERÇEKÇİ TÜRK LOJİSTİK FİLOLARI & PARAMETRELERİ (GEBZE & HADIMKÖY STANDARTLARI)
# ============================================================================
FLEET_PROFILES = [
    {
        "id": "borusan",
        "carrier_name": "Borusan Tedarik Zinciri ve Lojistik A.Ş.",
        "short_name": "Borusan Lojistik",
        "tax_id": "1800045192",
        "tio_number": "TİO-34-1002",
        "plate_codes": ["34 BRS", "41 BRS", "16 BRS"],
        "trailer_prefix": "34 BRS",
        "load_types": ["PALLET", "BULK", "CONTAINER"],
        "default_load_type": "PALLET",
        "cargos": [
            ("Endüstriyel Sıvı Yağ & Bakliyat", "PALLET", 32),
            ("Otomotiv Pres Parçaları & Rulo Sac", "BULK", 24),
            ("Ambalaj & Koli Karton Sevkiyatı", "PALLET", 30),
        ],
        "drivers": [
            ("Ahmet Yılmaz", "0532 991 22 33", "28910482910"),
            ("Selim Çelik", "0533 444 88 21", "19820391822"),
            ("Mustafa Kurt", "0530 812 34 56", "38291048290"),
        ],
        "items": [
            ("Yudum Ayçiçek Yağı 5L x 4", "KNT-YDM-01", "KOLI"),
            ("Filiz Makarna 500g x 20", "FLZ-MKR-02", "KOLI"),
            ("Duru Osmancık Pirinç 1kg x 12", "DRU-PRC-03", "KOLI"),
        ]
    },
    {
        "id": "ekol",
        "carrier_name": "Ekol Lojistik A.Ş.",
        "short_name": "Ekol Lojistik",
        "tax_id": "3320049182",
        "tio_number": "TİO-34-1180",
        "plate_codes": ["34 EKL", "41 EKL", "35 EKL"],
        "trailer_prefix": "34 EKL",
        "load_types": ["PALLET", "CONTAINER"],
        "default_load_type": "PALLET",
        "cargos": [
            ("Tekstil & Perakende Hazır Giyim", "PALLET", 33),
            ("Elektronik Komponent & Yan Sanayi", "PALLET", 28),
            ("Otomotiv Yedek Parça & Sensör", "PALLET", 26),
        ],
        "drivers": [
            ("Murat Arslan", "0532 555 10 24", "41920384918"),
            ("Barış Kaya", "0542 331 44 55", "52910293847"),
            ("Kenan Doğan", "0535 220 90 12", "63829102938"),
        ],
        "items": [
            ("LCW Askılı Tekstil Kolisi M-80", "LCW-TX-080", "ADET"),
            ("BOSCH Ön Fren Balata Takımı", "BSH-BRK-40", "KOLI"),
            ("Philips LED Panel Armatür", "PHL-LED-12", "KOLI"),
        ]
    },
    {
        "id": "mars",
        "carrier_name": "Mars Lojistik Uluslararası Taşımacılık A.Ş.",
        "short_name": "Mars Lojistik",
        "tax_id": "6120058890",
        "tio_number": "TİO-34-2201",
        "plate_codes": ["34 MRS", "35 MRS", "16 MRS"],
        "trailer_prefix": "34 MRS",
        "load_types": ["PALLET", "CONTAINER", "CHEMICAL"],
        "default_load_type": "PALLET",
        "cargos": [
            ("Kimyasal Hammadde & Polimer", "CHEMICAL", 24),
            ("İthalat Ambalajlı Tüketim Ürünleri", "PALLET", 32),
            ("Genel Kargo & Endüstriyel Hırdavat", "PALLET", 29),
        ],
        "drivers": [
            ("Dursun Şahin", "0530 111 99 00", "74829103948"),
            ("Cemil Aydın", "0532 770 19 23", "83920192837"),
            ("Oğuzhan Tekin", "0544 650 32 10", "94829103928"),
        ],
        "items": [
            ("Polimer Granül Hammadde 25kg", "PLM-GRN-25", "TORBA"),
            ("Endüstriyel Rulman Seti 6204", "RLM-SET-04", "KOLI"),
            ("Paketleme Streç Film 50cm", "STR-FLM-50", "RULO"),
        ]
    },
    {
        "id": "sutas",
        "carrier_name": "Sütaş Süt Ürünleri Frigo Lojistik",
        "short_name": "Sütaş Frigo",
        "tax_id": "7840028912",
        "tio_number": "TİO-16-0421",
        "plate_codes": ["16 STS", "34 STS", "16 BRB"],
        "trailer_prefix": "16 STS",
        "load_types": ["REEFER"],
        "default_load_type": "REEFER",
        "cargos": [
            ("Süt ve Süt Ürünleri (+4°C)", "REEFER", 33),
            ("Kaşar & Beyaz Peynir Soğuk Sevk", "REEFER", 30),
            ("Ayran & Yoğurt Frigo Dağıtım", "REEFER", 32),
        ],
        "drivers": [
            ("Recep Korkmaz", "0542 660 11 22", "18293049182"),
            ("Salih Bozkurt", "0533 112 33 44", "27384910293"),
            ("Hasan Özdemir", "0536 445 67 89", "36482910293"),
        ],
        "items": [
            ("Sütaş Tam Yağlı Süt 1L x 12", "STS-SUT-01", "KOLI"),
            ("Sütaş Taze Kaşar 500g x 24", "STS-KSR-02", "KOLI"),
            ("Sütaş Yayık Ayran 200ml x 20", "STS-AYR-03", "KOLI"),
        ]
    },
    {
        "id": "bim",
        "carrier_name": "BİM Birleşik Mağazalar Dağıtım Filosu",
        "short_name": "BİM Dağıtım",
        "tax_id": "1750051184",
        "tio_number": "TİO-34-8840",
        "plate_codes": ["34 BIM", "41 BIM", "35 BIM"],
        "trailer_prefix": "34 BIM",
        "load_types": ["PALLET", "REEFER"],
        "default_load_type": "PALLET",
        "cargos": [
            ("Hızlı Tüketim & Kuru Gıda (FMCG)", "PALLET", 33),
            ("Meyve & Sebze Soğuk Dağıtım (+6°C)", "REEFER", 28),
            ("Temizlik & Hijyen Ürünleri", "PALLET", 31),
        ],
        "drivers": [
            ("İbrahim Güler", "0532 888 12 34", "45678912301"),
            ("Gökhan Yıldız", "0542 777 33 49", "56789123412"),
            ("Erhan Akın", "0534 550 20 11", "67891234523"),
        ],
        "items": [
            ("Dost Yarım Yağlı Süt 1L x 12", "BIM-DST-01", "KOLI"),
            ("Aknaz Klasik Beyaz Peynir 1kg", "BIM-AKN-02", "KOLI"),
            ("Bind Çikolata Fıstıklı 100g x 24", "BIM-BND-03", "KUTU"),
        ]
    },
    {
        "id": "netlog",
        "carrier_name": "Netlog Lojistik Soğuk Zincir A.Ş.",
        "short_name": "Netlog Soğuk Zincir",
        "tax_id": "6310029311",
        "tio_number": "TİO-34-3091",
        "plate_codes": ["34 NTL", "16 NTL", "41 NTL"],
        "trailer_prefix": "34 NTL",
        "load_types": ["REEFER"],
        "default_load_type": "REEFER",
        "cargos": [
            ("Dondurulmuş Gıda (-18°C)", "REEFER", 32),
            ("Dondurulmuş Deniz Ürünleri (-22°C)", "REEFER", 26),
            ("Biyomedikal Soğuk İlaç & Aşı (+2/+8°C)", "REEFER", 20),
        ],
        "drivers": [
            ("Kemal Öztürk", "0555 222 66 77", "78912345634"),
            ("Burak Çetin", "0538 901 44 22", "89123456745"),
            ("Serdar Keskin", "0530 443 21 00", "91234567856"),
        ],
        "items": [
            ("SuperFresh Bezelye 450g x 20", "NTL-DND-01", "KOLI"),
            ("Dondurulmuş Karides 500g x 10", "NTL-KRD-02", "KOLI"),
            ("Biyomedikal Flakon Taşıma Kolisi", "NTL-MED-03", "KUTU"),
        ]
    },
    {
        "id": "horoz",
        "carrier_name": "Horoz Lojistik Kargo Hizmetleri A.Ş.",
        "short_name": "Horoz Lojistik",
        "tax_id": "4630018820",
        "tio_number": "TİO-34-1920",
        "plate_codes": ["34 HRZ", "06 HRZ", "35 HRZ"],
        "trailer_prefix": "34 HRZ",
        "load_types": ["PALLET"],
        "default_load_type": "PALLET",
        "cargos": [
            ("Beyaz Eşya & Dayanıklı Tüketim Malları", "PALLET", 28),
            ("Mobilya & E-Ticaret Hacimli Kargo", "PALLET", 25),
            ("Ev Elektroniği & Televizyon", "PALLET", 30),
        ],
        "drivers": [
            ("Fatih Demir", "0539 312 45 67", "12345678967"),
            ("Kadir Tan", "0543 890 12 34", "23456789178"),
            ("Ali Kemal Güven", "0532 601 29 88", "34567891289"),
        ],
        "items": [
            ("Arçelik 6103 Çamaşır Makinesi", "HRZ-ARC-01", "ADET"),
            ("Beko No-Frost Buzdolabı B100", "HRZ-BEK-02", "ADET"),
            ("Kelebek Mobilya Gardırop Kolisi", "HRZ-KLB-03", "KOLI"),
        ]
    }
]


class YardSimulator:
    """
    RampaRandevu Otonom Saha Trafik Simülatörü ve IoT Telemetri Motoru.
    
    Yetkinlikler:
    - 7/24 kesintisiz saha yaşam döngüsü simülasyonu.
    - PTS Plaka Okuma (ANPR), Giriş Kantarı (±%2 tolerans), Tampon Park (Waiting Lot).
    - Boşalan rampaya akıllı ve kuantum uyumlu otomatik çağrı (FIFO + Soğuk Zincir önceliği).
    - Körük yanaşması, DocuLog Vision AI irsaliye sayımı ve SAP MIGO 101 mal kabul mühürleme.
    - Çıkış kantarı dara/net ölçümü ve U-ETDS nizamiye çıkış bariyeri kapanışı.
    - Anlık WebSocket yayınları ve telemetri tampon hafızası.
    - API üzerinden dinamik kontrol, kaos senaryoları ve araç enjeksiyonu.
    """

    def __init__(self):
        self.is_running: bool = False
        self.interval_seconds: float = 4.0
        self.chaos_mode: bool = False
        self.auto_spawn: bool = True
        self.tick_count: int = 0
        self.last_tick_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        
        # Telemetry ring buffer (last 50 events)
        self.recent_events: collections.deque = collections.deque(maxlen=50)
        
        # Internal performance counters
        self.total_gate_in: int = 0
        self.total_gate_out: int = 0
        self.total_doculog_verified: int = 0
        self.total_discrepancies: int = 0

    def start(self, interval_seconds: Optional[float] = None) -> bool:
        """Otonom arka plan simülasyonunu başlatır."""
        if interval_seconds:
            self.interval_seconds = max(1.0, float(interval_seconds))
            
        if self._task and not self._task.done():
            self.is_running = True
            return True

        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Yard simulator background loop started (interval={self.interval_seconds}s)")
        return True

    def stop(self) -> bool:
        """Otonom arka plan simülasyonunu durdurur."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
        logger.info("Yard simulator background loop stopped")
        return False

    def toggle(
        self,
        enabled: Optional[bool] = None,
        interval_seconds: Optional[float] = None,
        chaos_mode: Optional[bool] = None,
        auto_spawn: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Simülasyon durumunu veya parametrelerini günceller."""
        if interval_seconds is not None:
            self.interval_seconds = max(1.0, float(interval_seconds))
        if chaos_mode is not None:
            self.chaos_mode = bool(chaos_mode)
        if auto_spawn is not None:
            self.auto_spawn = bool(auto_spawn)

        if enabled is None:
            # Toggle current state
            if self.is_running:
                self.stop()
            else:
                self.start()
        elif enabled:
            self.start()
        else:
            self.stop()

        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "chaos_mode": self.chaos_mode,
            "auto_spawn": self.auto_spawn,
            "tick_count": self.tick_count
        }

    async def _run_loop(self):
        """Sürekli arka plan görev döngüsü."""
        while self.is_running:
            try:
                await asyncio.sleep(self.interval_seconds)
                async with AsyncSessionLocal() as session:
                    await self.tick(session)
                    await session.commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Yard simulator cycle exception: {e}", exc_info=True)
                await asyncio.sleep(2.0)

    # ------------------------------------------------------------------------
    # SİMÜLASYON ADIMI (TICK ENGINE)
    # ------------------------------------------------------------------------
    async def tick(self, db: AsyncSession, force_spawn: bool = False) -> Dict[str, Any]:
        """
        Tek bir diskret simülasyon adımını çalıştırır:
        1. Çıkış kantarı ve sahadan ayrılış (COMPLETED -> DEPARTED)
        2. Mal kabul ve DocuLog sayımı (UNLOADING -> COMPLETED)
        3. Rampa körüğüne yanaşma (CALLED -> UNLOADING)
        4. Boşalan rampalara tampon parktan araç çağırma (WAITING_LOT -> CALLED)
        5. Nizamiye kapı girişi, PTS okuma & kantar (SCHEDULED -> WAITING_LOT)
        6. Otonom tır akışı sağlama (Yeni tır oluşturup kapıya yaklaştırma)
        """
        self.tick_count += 1
        self.last_tick_at = datetime.now()
        actions_taken = []

        # 1. ÇIKIŞ KANTARI & GATE-OUT (COMPLETED -> DEPARTED)
        departed_actions = await self._process_departures(db)
        actions_taken.extend(departed_actions)

        # 2. MAL KABUL & DOCULOG SAYIMI (UNLOADING -> COMPLETED)
        completed_actions = await self._process_unload_completions(db)
        actions_taken.extend(completed_actions)

        # 3. KÖRÜĞE YANAŞMA & BOŞALTMA BAŞLATMA (CALLED -> UNLOADING)
        docked_actions = await self._process_dock_dockings(db)
        actions_taken.extend(docked_actions)

        # 4. TAMPON PARKTAN BOŞ RAMPAYA ÇAĞRI (WAITING_LOT -> CALLED)
        called_actions = await self._process_dock_assignments(db)
        actions_taken.extend(called_actions)

        # 5. NİZAMİYE PTS & GİRİŞ KANTARI (SCHEDULED -> WAITING_LOT)
        arrival_actions = await self._process_scheduled_arrivals(db)
        actions_taken.extend(arrival_actions)

        # 6. OTONOM ARAÇ AKIŞI (Yeni araç üretimi)
        if self.auto_spawn or force_spawn:
            spawn_action = await self._process_auto_spawn(db, force=force_spawn)
            if spawn_action:
                actions_taken.append(spawn_action)

        # Özet saha durumu
        summary = await self._get_quick_summary(db)

        return {
            "status": "success",
            "tick": self.tick_count,
            "timestamp": self.last_tick_at.isoformat(),
            "events_count": len(actions_taken),
            "events": actions_taken,
            "summary": summary
        }

    # ------------------------------------------------------------------------
    # ADIM 1: ÇIKIŞ KANTARI VE GATE-OUT
    # ------------------------------------------------------------------------
    async def _process_departures(self, db: AsyncSession) -> List[Dict[str, Any]]:
        actions = []
        res = await db.execute(
            select(Appointment)
            .where(Appointment.status == "COMPLETED")
            .order_by(Appointment.actual_dock_out.asc())
            .limit(2)
        )
        completed_apps = res.scalars().all()

        for app in completed_apps:
            now = datetime.now()
            # Çıkış kantarı dara tartımı
            base_tare = 15200.0 if not app.weighbridge_tare_kg else app.weighbridge_tare_kg
            measured_tare = round(base_tare * (1 + random.uniform(-0.01, 0.01)), 1)
            
            # Net ağırlık hesaplama
            if app.weighbridge_gross_kg:
                measured_net = round(app.weighbridge_gross_kg - measured_tare, 1)
            else:
                measured_net = round(app.estimated_pallets * 650.0, 1)
                app.weighbridge_gross_kg = round(measured_tare + measured_net, 1)

            app.weighbridge_tare_kg = measured_tare
            app.weighbridge_net_kg = measured_net
            app.status = "DEPARTED"
            app.actual_gate_out = now

            # Çıkış kapısı ve kantar logları
            db.add(GateLog(
                appointment_id=app.id,
                event_type="WEIGHBRIDGE_EXIT",
                gate_operator="Kantar-02 (Çıkış)",
                notes=f"Çıkış kantarı tamamlandı. Dara: {measured_tare:,.1f} kg | Boşaltılan Net: {measured_net:,.1f} kg"
            ))
            db.add(GateLog(
                appointment_id=app.id,
                event_type="GATE_OUT",
                gate_operator="Nizamiye-01",
                notes=f"Araç nizamiye çıkış bariyerinden geçti. Tesisten ayrıldı. U-ETDS sefer kapanışı tamamlandı."
            ))

            self.total_gate_out += 1
            log_item = {
                "timestamp": now.isoformat(),
                "event": "GATE_OUT",
                "plate": app.vehicle_plate,
                "carrier": app.carrier_name,
                "detail": f"Çıkış Kantarı: Dara {measured_tare:,.0f} kg / Net {measured_net:,.0f} kg | Saha Terk Edildi"
            }
            self.recent_events.append(log_item)
            actions.append(log_item)

            # WebSocket Broadcast
            await ws_hub.broadcast_event("WEIGHBRIDGE_EXIT_MEASURED", {
                "appointment_id": app.id,
                "vehicle_plate": app.vehicle_plate,
                "tare_kg": measured_tare,
                "net_kg": measured_net,
                "discrepancy": app.weighbridge_discrepancy
            })
            await ws_hub.broadcast_event("VEHICLE_DEPARTED", {
                "appointment_id": app.id,
                "vehicle_plate": app.vehicle_plate,
                "carrier_name": app.carrier_name,
                "actual_gate_out": now.isoformat()
            })

        return actions

    # ------------------------------------------------------------------------
    # ADIM 2: MAL KABUL & DOCULOG SAYIMI (UNLOADING -> COMPLETED)
    # ------------------------------------------------------------------------
    async def _process_unload_completions(self, db: AsyncSession) -> List[Dict[str, Any]]:
        actions = []
        res = await db.execute(
            select(Appointment)
            .where(Appointment.status == "UNLOADING")
            .order_by(Appointment.actual_dock_in.asc())
            .limit(2)
        )
        unloading_apps = res.scalars().all()

        for app in unloading_apps:
            now = datetime.now()
            # DocuLog Vision AI İrsaliye Sayım Kontrolü
            is_discrepancy = self.chaos_mode and random.random() < 0.25
            doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

            if is_discrepancy:
                doc_status = "DISCREPANCY"
                sap_code = "103" # Bloke Giriş
                receipt_status = "DISCREPANCY"
                summary_text = (
                    f"DocuLog Vision AI: {app.estimated_pallets} palet sayımında 2 hasarlı koli ve 1 eksik koli tespit edildi. "
                    f"SAP 103 Bloke Giriş açıldı."
                )
                self.total_discrepancies += 1
            else:
                doc_status = "MATCH_OK"
                sap_code = "101" # Sağlam Giriş
                receipt_status = "APPROVED"
                summary_text = (
                    f"DocuLog Vision AI: {app.estimated_pallets} palet barkod ve koli sayımı %100 doğrulukla teyit edildi. "
                    f"Hasarsız teslim, SAP 101 tam giriş onaylandı."
                )

            app.doculog_status = doc_status
            app.doculog_document_id = doc_id
            app.doculog_summary = summary_text
            app.status = "COMPLETED"
            app.actual_dock_out = now

            # Rampayı serbest bırak
            if app.dock_id:
                d_res = await db.execute(select(Dock).where(Dock.id == app.dock_id))
                dock = d_res.scalars().first()
                if dock:
                    dock.status = "IDLE"

            # Mal Kabul Belgesi (GoodsReceipt & Items) oluştur (eğer daha önce yoksa)
            gr_res = await db.execute(select(GoodsReceipt).where(GoodsReceipt.appointment_id == app.id))
            if not gr_res.scalars().first():
                gr = GoodsReceipt(
                    appointment_id=app.id,
                    waybill_number=app.waybill_number or f"GIB2026{random.randint(10000000, 99999999)}",
                    e_waybill_uuid=app.e_waybill_uuid or str(uuid.uuid4()),
                    supplier_vkn=app.carrier_tax_id or "1800045192",
                    supplier_title=app.carrier_name,
                    sap_movement_code=sap_code,
                    uetds_reference_number=f"UETDS-{uuid.uuid4().hex[:8].upper()}",
                    status=receipt_status,
                    warehouse_notes=summary_text
                )
                db.add(gr)
                await db.flush()

                # İlgili filonun kalemlerini üret
                fleet = self._match_fleet(app.carrier_name)
                items_data = fleet.get("items", [("Genel Kargo Kolisi", "GEN-01", "KOLI")])
                for idx, (desc, code, uom) in enumerate(items_data, start=1):
                    damaged = 2.0 if is_discrepancy and idx == 1 else 0.0
                    missing = 1.0 if is_discrepancy and idx == 2 else 0.0
                    db.add(GoodsReceiptItem(
                        goods_receipt_id=gr.id,
                        line_number=idx,
                        material_code=code,
                        description=desc,
                        dispatched_qty=float(app.estimated_pallets * 10),
                        received_qty=float(app.estimated_pallets * 10 - missing),
                        damaged_qty=damaged,
                        missing_qty=missing,
                        uom=uom,
                        inspection_status="DAMAGED" if damaged > 0 else "OK"
                    ))

            # Gate Log
            db.add(GateLog(
                appointment_id=app.id,
                event_type="UNLOAD_END",
                gate_operator="Rampa Amiri",
                notes=f"DocuLog sayımı tamamlandı ({doc_status}). Rampa serbest bırakıldı."
            ))

            self.total_doculog_verified += 1
            log_item = {
                "timestamp": now.isoformat(),
                "event": "DOCULOG_COMPLETED",
                "plate": app.vehicle_plate,
                "carrier": app.carrier_name,
                "detail": f"{app.estimated_pallets} Palet DocuLog AI ile Sayıldı ({doc_status}) -> Rampa Boşaltıldı"
            }
            self.recent_events.append(log_item)
            actions.append(log_item)

            # WebSocket Broadcast
            await ws_hub.broadcast_event("DOCULOG_WAYBILL_MATCHED", {
                "appointment_id": app.id,
                "vehicle_plate": app.vehicle_plate,
                "doculog_document_id": doc_id,
                "status": doc_status,
                "summary": summary_text
            })
            await ws_hub.broadcast_event("DOCK_OPERATION_COMPLETED", {
                "appointment_id": app.id,
                "dock_id": app.dock_id,
                "status": "COMPLETED"
            })

        return actions

    # ------------------------------------------------------------------------
    # ADIM 3: KÖRÜĞE YANAŞMA & BOŞALTMA BAŞLATMA (CALLED -> UNLOADING)
    # ------------------------------------------------------------------------
    async def _process_dock_dockings(self, db: AsyncSession) -> List[Dict[str, Any]]:
        actions = []
        res = await db.execute(
            select(Appointment)
            .where(Appointment.status == "CALLED")
            .order_by(Appointment.actual_dock_in.asc())
            .limit(2)
        )
        called_apps = res.scalars().all()

        for app in called_apps:
            now = datetime.now()
            app.status = "UNLOADING"
            
            dock_num = "Rampa"
            if app.dock_id:
                d_res = await db.execute(select(Dock).where(Dock.id == app.dock_id))
                dock = d_res.scalars().first()
                if dock:
                    dock.status = "OCCUPIED"
                    dock_num = dock.dock_number

            db.add(GateLog(
                appointment_id=app.id,
                event_type="UNLOAD_START",
                gate_operator="Rampa Operatörü",
                notes=f"{dock_num} körüğüne yanaşıldı. Kilit takozları sabitlendi. Forklift boşaltma operasyonu başladı."
            ))

            log_item = {
                "timestamp": now.isoformat(),
                "event": "UNLOAD_STARTED",
                "plate": app.vehicle_plate,
                "carrier": app.carrier_name,
                "detail": f"{dock_num} Körüğüne Kilitlendi -> Forklift Boşaltması Aktif ({app.estimated_pallets} palet)"
            }
            self.recent_events.append(log_item)
            actions.append(log_item)

            await ws_hub.broadcast_event("DOCK_OPERATION_STARTED", {
                "appointment_id": app.id,
                "dock_id": app.dock_id,
                "dock_number": dock_num,
                "vehicle_plate": app.vehicle_plate
            })

        return actions

    # ------------------------------------------------------------------------
    # ADIM 4: TAMPON PARKTAN BOŞ RAMPAYA ÇAĞRI (WAITING_LOT -> CALLED)
    # ------------------------------------------------------------------------
    async def _process_dock_assignments(self, db: AsyncSession) -> List[Dict[str, Any]]:
        actions = []
        # Boş ve aktif rampaları çek
        d_res = await db.execute(select(Dock).where(Dock.status == "IDLE", Dock.is_active == True))
        idle_docks = list(d_res.scalars().all())
        if not idle_docks:
            return actions

        # Tampon parktaki araçları çek (Soğuk zincir ve erken slot öncelikli)
        w_res = await db.execute(
            select(Appointment)
            .where(Appointment.status == "WAITING_LOT")
            .order_by(
                case((Appointment.load_type == "REEFER", 0), else_=1),
                Appointment.slot_start.asc()
            )
        )
        waiting_apps = list(w_res.scalars().all())
        if not waiting_apps:
            return actions

        for app in waiting_apps:
            if not idle_docks:
                break

            # Uygun rampa bul (Soğuk yükse COLD_REEFER, normal ise SHELTER/HYDRAULIC)
            matched_dock: Optional[Dock] = None
            for d in idle_docks:
                if app.load_type == "REEFER":
                    if d.dock_type == "COLD_REEFER":
                        matched_dock = d
                        break
                else:
                    if d.dock_type != "COLD_REEFER" and d.max_pallets >= app.estimated_pallets:
                        matched_dock = d
                        break

            # Eğer tam eşleşme bulunamadıysa ve soğuk değilse herhangi bir müsait rampa
            if not matched_dock and app.load_type != "REEFER":
                for d in idle_docks:
                    if d.dock_type != "COLD_REEFER":
                        matched_dock = d
                        break

            if matched_dock:
                idle_docks.remove(matched_dock)
                now = datetime.now()

                app.dock_id = matched_dock.id
                app.status = "CALLED"
                app.actual_dock_in = now
                matched_dock.status = "CALLING"

                db.add(GateLog(
                    appointment_id=app.id,
                    event_type="CALL_TO_DOCK",
                    gate_operator="Otonom Rampa Tahsis Motoru",
                    notes=f"Araç {matched_dock.dock_number} nolu rampaya otomatik çağrıldı. Şoföre SMS fırlatıldı."
                ))

                log_item = {
                    "timestamp": now.isoformat(),
                    "event": "VEHICLE_CALLED",
                    "plate": app.vehicle_plate,
                    "carrier": app.carrier_name,
                    "detail": f"{matched_dock.dock_number} Tahsis Edildi -> Şoföre Çağrı Gönderildi ({app.load_type})"
                }
                self.recent_events.append(log_item)
                actions.append(log_item)

                await ws_hub.broadcast_event("VEHICLE_CALLED_TO_DOCK", {
                    "appointment_id": app.id,
                    "vehicle_plate": app.vehicle_plate,
                    "driver_phone": app.driver_phone,
                    "dock_id": matched_dock.id,
                    "dock_number": matched_dock.dock_number,
                    "tracking_token": app.tracking_token
                })

        return actions

    # ------------------------------------------------------------------------
    # ADIM 5: NİZAMİYE PTS & GİRİŞ KANTARI (SCHEDULED -> WAITING_LOT)
    # ------------------------------------------------------------------------
    async def _process_scheduled_arrivals(self, db: AsyncSession) -> List[Dict[str, Any]]:
        actions = []
        res = await db.execute(
            select(Appointment)
            .where(Appointment.status == "SCHEDULED")
            .order_by(Appointment.slot_start.asc())
            .limit(2)
        )
        scheduled_apps = res.scalars().all()

        for app in scheduled_apps:
            now = datetime.now()
            # Giriş kantarı tartımı (±%2 tolerans)
            nominal_tare = 15200.0
            nominal_net = app.estimated_pallets * 680.0
            nominal_gross = nominal_tare + nominal_net
            
            # Tolerans sapması
            if self.chaos_mode and random.random() < 0.2:
                # Kaos modu kantar fire aşımı (%4 - %6 sapma)
                deviation = random.choice([random.uniform(0.04, 0.06), random.uniform(-0.06, -0.04)])
                is_discrepancy = True
                self.total_discrepancies += 1
            else:
                deviation = random.uniform(-0.018, 0.018) # Standart ±%2 yasal tolerans
                is_discrepancy = False

            measured_gross = round(nominal_gross * (1.0 + deviation), 1)
            ticket_no = f"KNT-2026-{random.randint(10000, 99999)}"

            app.status = "WAITING_LOT"
            app.actual_gate_in = now
            app.weighbridge_ticket_no = ticket_no
            app.weighbridge_gross_kg = measured_gross
            app.weighbridge_discrepancy = is_discrepancy

            # Gate Log
            pts_acc = round(random.uniform(99.1, 99.8), 1)
            db.add(GateLog(
                appointment_id=app.id,
                event_type="GATE_IN",
                gate_operator="Nizamiye ANPR/Kantar",
                notes=f"PTS Kamera 01 plaka okudu (%{pts_acc}). Giriş kantarı: {measured_gross:,.1f} kg. Bilet: {ticket_no}. Tır Parkı Bölge B'ye alındı."
            ))

            self.total_gate_in += 1
            log_item = {
                "timestamp": now.isoformat(),
                "event": "PTS_GATE_IN",
                "plate": app.vehicle_plate,
                "carrier": app.carrier_name,
                "detail": f"PTS Plaka Okundu (%{pts_acc}) | Kantar: {measured_gross:,.0f} kg ({ticket_no}) -> Tır Parkı B"
            }
            self.recent_events.append(log_item)
            actions.append(log_item)

            # WebSocket Broadcasts
            await ws_hub.broadcast_event("PTS_PLATE_READ", {
                "camera_id": "PTS-CAM-01",
                "vehicle_plate": app.vehicle_plate,
                "confidence": pts_acc,
                "timestamp": now.isoformat()
            })
            await ws_hub.broadcast_event("WEIGHBRIDGE_ENTRY_MEASURED", {
                "ticket_no": ticket_no,
                "vehicle_plate": app.vehicle_plate,
                "gross_kg": measured_gross,
                "discrepancy": is_discrepancy
            })
            await ws_hub.broadcast_event("VEHICLE_ARRIVED_AT_GATE", {
                "appointment_id": app.id,
                "vehicle_plate": app.vehicle_plate,
                "carrier_name": app.carrier_name,
                "actual_gate_in": now.isoformat(),
                "status": app.status
            })

        return actions

    # ------------------------------------------------------------------------
    # ADIM 6: OTONOM ARAÇ AKIŞI (Yeni araç üretimi)
    # ------------------------------------------------------------------------
    async def _process_auto_spawn(self, db: AsyncSession, force: bool = False) -> Optional[Dict[str, Any]]:
        # Sahadaki toplam aktif araç sayısını kontrol et
        res = await db.execute(
            select(func.count(Appointment.id))
            .where(Appointment.status.in_(["WAITING_LOT", "CALLED", "UNLOADING"]))
        )
        active_count = res.scalar() or 0

        # Sahada 6'dan az araç varsa veya zorunlu kılınmışsa yeni araç üret
        if not force and active_count >= 6:
            return None

        # Rastgele filo seç
        fleet = random.choice(FLEET_PROFILES)
        cargo_info = random.choice(fleet["cargos"])
        driver_info = random.choice(fleet["drivers"])

        plate_code = random.choice(fleet["plate_codes"])
        plate_num = random.randint(100, 999)
        vehicle_plate = f"{plate_code} {plate_num}"
        trailer_plate = f"{fleet['trailer_prefix']} {random.randint(100, 999)}"

        now = datetime.now()
        slot_duration = QuantumSlotEngine.calculate_slot_duration(cargo_info[2], cargo_info[1])

        # Kantar brüt tartımı (±%2 tolerans)
        nominal_tare = 15400.0
        nominal_net = cargo_info[2] * 650.0
        nominal_gross = nominal_tare + nominal_net
        
        is_discrepancy = self.chaos_mode and random.random() < 0.2
        if is_discrepancy:
            dev = random.choice([random.uniform(0.04, 0.06), random.uniform(-0.06, -0.04)])
            self.total_discrepancies += 1
        else:
            dev = random.uniform(-0.018, 0.018)

        measured_gross = round(nominal_gross * (1.0 + dev), 1)
        ticket_no = f"KNT-2026-{random.randint(10000, 99999)}"
        pts_acc = round(random.uniform(99.2, 99.9), 1)

        # Appointment oluştur ve doğrudan tampon parka al (PTS + Kantar geçilmiş halde)
        app = Appointment(
            carrier_name=fleet["carrier_name"],
            carrier_tax_id=fleet["tax_id"],
            tio_number=fleet["tio_number"],
            vehicle_plate=vehicle_plate,
            trailer_plate=trailer_plate,
            driver_name=driver_info[0],
            driver_phone=driver_info[1],
            driver_tckn=driver_info[2],
            slot_start=now,
            slot_end=now + timedelta(minutes=slot_duration),
            actual_gate_in=now,
            cargo_type=cargo_info[0],
            load_type=cargo_info[1],
            estimated_pallets=cargo_info[2],
            pallet_type="EPAL / Euro Palet",
            calculated_duration_minutes=slot_duration,
            weighbridge_ticket_no=ticket_no,
            weighbridge_gross_kg=measured_gross,
            weighbridge_discrepancy=is_discrepancy,
            po_number=f"PO-4500{random.randint(100000, 999999)}",
            waybill_number=f"GIB2026{random.randint(10000000, 99999999)}",
            e_waybill_uuid=str(uuid.uuid4()),
            status="WAITING_LOT",
            sla_status="ON_TIME",
            tracking_token=f"RR-{uuid.uuid4().hex[:6].upper()}"
        )
        db.add(app)
        await db.flush()

        db.add(GateLog(
            appointment_id=app.id,
            event_type="GATE_IN",
            gate_operator="Nizamiye-01 (Otonom ANPR)",
            notes=f"PTS Kamera 01 plaka okudu (%{pts_acc}). Giriş kantarı: {measured_gross:,.1f} kg ({ticket_no}). Tır parkına yönlendirildi."
        ))

        self.total_gate_in += 1
        log_item = {
            "timestamp": now.isoformat(),
            "event": "FLEET_SPAWN_GATE_IN",
            "plate": app.vehicle_plate,
            "carrier": fleet["short_name"],
            "detail": f"Otonom Filo: {fleet['short_name']} ({app.vehicle_plate}) Kapıya Yanaştı | Brüt: {measured_gross:,.0f} kg"
        }
        self.recent_events.append(log_item)

        # Broadcast
        await ws_hub.broadcast_event("PTS_PLATE_READ", {
            "camera_id": "PTS-CAM-01",
            "vehicle_plate": app.vehicle_plate,
            "confidence": pts_acc,
            "timestamp": now.isoformat()
        })
        await ws_hub.broadcast_event("WEIGHBRIDGE_ENTRY_MEASURED", {
            "ticket_no": ticket_no,
            "vehicle_plate": app.vehicle_plate,
            "gross_kg": measured_gross,
            "discrepancy": is_discrepancy
        })
        await ws_hub.broadcast_event("VEHICLE_ARRIVED_AT_GATE", {
            "appointment_id": app.id,
            "vehicle_plate": app.vehicle_plate,
            "carrier_name": app.carrier_name,
            "actual_gate_in": now.isoformat(),
            "status": app.status
        })

        return log_item

    # ------------------------------------------------------------------------
    # ÖZEL ARAÇ ENJEKSİYONU (INJECT TRUCK)
    # ------------------------------------------------------------------------
    async def inject_truck(
        self,
        db: AsyncSession,
        vehicle_plate: Optional[str] = None,
        carrier_name: Optional[str] = None,
        load_type: Optional[str] = None,
        cargo_type: Optional[str] = None,
        estimated_pallets: Optional[int] = None,
        driver_name: Optional[str] = None,
        driver_phone: Optional[str] = None,
        priority: Optional[str] = "NORMAL",
        force_discrepancy: bool = False
    ) -> Appointment:
        """
        Kullanıcı veya API tarafından istenen özelliklerdeki bir tırı
        anında nizamiye kapısına yaklaştırır ve PTS/Kantar döngüsünü işletir.
        """
        # Filo seçimi veya eşleme
        fleet = self._match_fleet(carrier_name) if carrier_name else random.choice(FLEET_PROFILES)
        
        # Plaka
        if not vehicle_plate:
            code = random.choice(fleet["plate_codes"])
            vehicle_plate = f"{code} {random.randint(100, 999)}"
        else:
            vehicle_plate = vehicle_plate.upper().strip()

        # Dorse
        trailer_plate = f"{fleet['trailer_prefix']} {random.randint(100, 999)}"

        # Yük tipi & palet
        final_load_type = load_type or fleet.get("default_load_type", "PALLET")
        final_pallets = estimated_pallets or (33 if final_load_type == "REEFER" else 30)
        final_cargo = cargo_type or (
            "Soğuk Zincir Süt & Peynir (+4°C)" if final_load_type == "REEFER"
            else "Kuru Gıda & Hızlı Tüketim (FMCG)"
        )

        # Şoför bilgisi
        default_driver = fleet["drivers"][0]
        final_driver = driver_name or default_driver[0]
        final_phone = driver_phone or default_driver[1]
        final_tckn = default_driver[2]

        now = datetime.now()
        slot_duration = QuantumSlotEngine.calculate_slot_duration(final_pallets, final_load_type)

        # Kantar tartımı (±%2 tolerans veya zorunlu fire)
        nominal_tare = 15300.0
        nominal_net = final_pallets * 660.0
        nominal_gross = nominal_tare + nominal_net

        if force_discrepancy or (self.chaos_mode and random.random() < 0.25):
            dev = random.choice([random.uniform(0.04, 0.065), random.uniform(-0.065, -0.04)])
            is_discrepancy = True
            self.total_discrepancies += 1
        else:
            dev = random.uniform(-0.018, 0.018)
            is_discrepancy = False

        measured_gross = round(nominal_gross * (1.0 + dev), 1)
        ticket_no = f"KNT-2026-{random.randint(10000, 99999)}"
        pts_acc = round(random.uniform(99.4, 99.9), 1)

        sla = "CRITICAL_DEMURRAGE" if priority == "URGENT_COLD_CHAIN" else "ON_TIME"

        app = Appointment(
            carrier_name=carrier_name or fleet["carrier_name"],
            carrier_tax_id=fleet["tax_id"],
            tio_number=fleet["tio_number"],
            vehicle_plate=vehicle_plate,
            trailer_plate=trailer_plate,
            driver_name=final_driver,
            driver_phone=final_phone,
            driver_tckn=final_tckn,
            slot_start=now,
            slot_end=now + timedelta(minutes=slot_duration),
            actual_gate_in=now,
            cargo_type=final_cargo,
            load_type=final_load_type,
            estimated_pallets=final_pallets,
            pallet_type="EPAL / Euro Palet",
            calculated_duration_minutes=slot_duration,
            weighbridge_ticket_no=ticket_no,
            weighbridge_gross_kg=measured_gross,
            weighbridge_discrepancy=is_discrepancy,
            po_number=f"PO-4500{random.randint(100000, 999999)}",
            waybill_number=f"GIB2026{random.randint(10000000, 99999999)}",
            e_waybill_uuid=str(uuid.uuid4()),
            status="WAITING_LOT",
            sla_status=sla,
            tracking_token=f"RR-{uuid.uuid4().hex[:6].upper()}"
        )
        db.add(app)
        await db.flush()

        db.add(GateLog(
            appointment_id=app.id,
            event_type="GATE_IN",
            gate_operator="Nizamiye-01 (Kullanıcı Enjeksiyonu)",
            notes=f"Özel enjeksiyon: PTS Okundu (%{pts_acc}). Kantar: {measured_gross:,.1f} kg. Öncelik: {priority}."
        ))

        self.total_gate_in += 1
        log_item = {
            "timestamp": now.isoformat(),
            "event": "INJECTED_TRUCK_GATE_IN",
            "plate": app.vehicle_plate,
            "carrier": app.carrier_name,
            "detail": f"Manuel Tır Enjekte Edildi: {app.vehicle_plate} | {final_load_type} ({final_pallets} palet) | Kantar: {measured_gross:,.0f} kg"
        }
        self.recent_events.append(log_item)

        # WebSocket Broadcast
        await ws_hub.broadcast_event("PTS_PLATE_READ", {
            "camera_id": "PTS-CAM-01",
            "vehicle_plate": app.vehicle_plate,
            "confidence": pts_acc,
            "timestamp": now.isoformat()
        })
        await ws_hub.broadcast_event("WEIGHBRIDGE_ENTRY_MEASURED", {
            "ticket_no": ticket_no,
            "vehicle_plate": app.vehicle_plate,
            "gross_kg": measured_gross,
            "discrepancy": is_discrepancy
        })
        await ws_hub.broadcast_event("VEHICLE_ARRIVED_AT_GATE", {
            "appointment_id": app.id,
            "vehicle_plate": app.vehicle_plate,
            "carrier_name": app.carrier_name,
            "actual_gate_in": now.isoformat(),
            "status": app.status
        })

        return app

    # ------------------------------------------------------------------------
    # TELEMETRİ & DURUM ANALİTİĞİ
    # ------------------------------------------------------------------------
    async def get_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Tüm saha telemetrisini ve simülasyon durumunu derler."""
        # Docks
        d_res = await db.execute(select(Dock))
        all_docks = d_res.scalars().all()
        total_docks = len(all_docks)
        occupied_docks = sum(1 for d in all_docks if d.status == "OCCUPIED")
        calling_docks = sum(1 for d in all_docks if d.status == "CALLING")
        idle_docks = sum(1 for d in all_docks if d.status == "IDLE")

        # Appointments count by status
        res_apps = await db.execute(select(Appointment))
        all_apps = res_apps.scalars().all()

        waiting_lot = sum(1 for a in all_apps if a.status == "WAITING_LOT")
        called = sum(1 for a in all_apps if a.status == "CALLED")
        unloading = sum(1 for a in all_apps if a.status == "UNLOADING")
        completed = sum(1 for a in all_apps if a.status == "COMPLETED")
        departed = sum(1 for a in all_apps if a.status == "DEPARTED")
        discrepancies = sum(1 for a in all_apps if a.weighbridge_discrepancy)

        active_in_yard = waiting_lot + called + unloading + completed
        occupancy_rate = round((occupied_docks / total_docks * 100), 1) if total_docks > 0 else 0.0

        # Ortalama saha kalış süresi (dwell time)
        dwell_times = []
        for a in all_apps:
            if a.actual_gate_in:
                end_time = a.actual_gate_out or datetime.now()
                dwell_times.append((end_time - a.actual_gate_in).total_seconds() / 60.0)
        avg_dwell = round(sum(dwell_times) / len(dwell_times), 1) if dwell_times else 45.0

        return {
            "is_running": self.is_running,
            "tick_count": self.tick_count,
            "interval_seconds": self.interval_seconds,
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
            "chaos_mode": self.chaos_mode,
            "auto_spawn": self.auto_spawn,
            "active_trucks_in_yard": active_in_yard,
            "waiting_in_lot": waiting_lot,
            "calling_to_dock": called,
            "at_docks": unloading,
            "completed_today": completed + departed,
            "departed_total": departed,
            "docks_occupancy_rate": occupancy_rate,
            "docks_breakdown": {
                "total": total_docks,
                "idle": idle_docks,
                "calling": calling_docks,
                "occupied": occupied_docks
            },
            "telemetry": {
                "gate_flow_per_hour": max(12, self.total_gate_in * 3),
                "avg_dwell_time_minutes": avg_dwell,
                "scale_discrepancy_count": discrepancies,
                "moxa_gateway_status": "ONLINE",
                "anpr_camera_fps": 30,
                "scale_calibration": "OIML_R76_CLASS_III_APPROVED",
                "recent_events": list(self.recent_events)
            }
        }

    async def _get_quick_summary(self, db: AsyncSession) -> Dict[str, Any]:
        d_res = await db.execute(select(Dock.status))
        dock_statuses = d_res.scalars().all()
        
        a_res = await db.execute(select(Appointment.status))
        app_statuses = a_res.scalars().all()

        return {
            "waiting_lot": sum(1 for s in app_statuses if s == "WAITING_LOT"),
            "called": sum(1 for s in app_statuses if s == "CALLED"),
            "unloading": sum(1 for s in app_statuses if s == "UNLOADING"),
            "completed": sum(1 for s in app_statuses if s == "COMPLETED"),
            "idle_docks": sum(1 for s in dock_statuses if s == "IDLE"),
            "occupied_docks": sum(1 for s in dock_statuses if s == "OCCUPIED")
        }

    def _match_fleet(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        for f in FLEET_PROFILES:
            if f["id"] in q or f["short_name"].lower() in q or f["carrier_name"].lower() in q:
                return f
        return FLEET_PROFILES[0]


# Global singleton instance
yard_simulator = YardSimulator()
