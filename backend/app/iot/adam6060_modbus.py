"""
Bariyer Motoru ve Manyetik Sensörler için Advantech ADAM-6060 Modbus TCP Röle Sürücüsü.
6x Dijital Giriş (DI) ve 6x Röle Çıkışı (DO) yönetimi.
"""

import asyncio
import struct
import socket
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("dockpulse.iot.adam6060")

class SafetyInterlockException(Exception):
    """Bariyer altında araç varken (Güvenlik Fotoseli kesilmişken) kapatma komutu engellendiğinde fırlatılır."""
    pass

@dataclass
class ADAM6060State:
    # 6x Dijital Giriş (DI0..DI5)
    # DI0: Araç Giriş Manyetik Döngüsü (Inbound Loop)
    # DI1: Bariyer Altı Güvenlik Fotoseli (Safety Photocell: True = Güvenli/Açık, False = Işın Kesildi/Araç Var)
    # DI2: Bariyer Tam Açık Sınır Anahtarı (Limit Switch Open)
    # DI3: Bariyer Tam Kapalı Sınır Anahtarı (Limit Switch Closed)
    # DI4: Çıkış Manyetik Döngüsü (Exit Loop)
    # DI5: Acil Durum Butonu (Emergency Button)
    di: Dict[int, bool] = field(default_factory=lambda: {
        0: False,  # Loop
        1: True,   # Photocell Safe (True = Clear / No obstruction)
        2: False,  # Open limit
        3: True,   # Closed limit (barrier is initially down)
        4: False,  # Exit loop
        5: False   # Emergency
    })

    # 6x Röle Çıkışı (DO0..DO5)
    # DO0: Bariyer Açma Darbesi (Open Pulse)
    # DO1: Bariyer Kapama Darbesi (Close Pulse)
    # DO2: Yeşil Geçiş Trafik Işığı (Traffic Light Green)
    # DO3: Kırmızı Dur Trafik Işığı (Traffic Light Red)
    # DO4: Sesli İkaz Sireni (Warning Siren)
    # DO5: Yardımcı Röle (Aux)
    do: Dict[int, bool] = field(default_factory=lambda: {
        0: False,
        1: False,
        2: False,
        3: True,   # Initially RED light
        4: False,
        5: False
    })
    
    last_pulse_timestamp: Optional[datetime] = None
    connected: bool = True
    connection_type: str = "SIMULATION"

class ADAM6060Controller:
    """
    Advantech ADAM-6060 Modbus TCP Sürücüsü ve Endüstriyel Donanım Simülatörü.
    Gerçek donanım IP'sine bağlanabilir veya test ortamında hassas dijital I/O simülasyonu yürütür.
    """

    def __init__(self, host: str = "192.168.1.200", port: int = 502, simulation_mode: bool = True):
        self.host = host
        self.port = port
        self.simulation_mode = simulation_mode
        self.state = ADAM6060State()
        self._lock = asyncio.Lock()
        self._tx_id = 0

    def _next_tx_id(self) -> int:
        self._tx_id = (self._tx_id + 1) & 0xFFFF
        return self._tx_id

    async def read_discrete_inputs(self) -> Dict[str, Any]:
        """
        DI0..DI5 dijital girişleri okur (Manyetik loop, fotosel, sınır anahtarları).
        """
        async with self._lock:
            if not self.simulation_mode:
                # Gerçek Modbus TCP üzerinden okuma (Function Code 0x02: Read Discrete Inputs)
                try:
                    await self._modbus_read_inputs()
                except Exception as e:
                    logger.warning(f"ADAM-6060 TCP okuma hatası, yerel önbellek kullanılıyor: {e}")

            return {
                "inbound_loop_active": self.state.di[0],
                "safety_photocell_clear": self.state.di[1], # True = ışın açık (güvenli)
                "barrier_open_limit": self.state.di[2],
                "barrier_closed_limit": self.state.di[3],
                "exit_loop_active": self.state.di[4],
                "emergency_button_active": self.state.di[5],
                "raw_inputs": dict(self.state.di)
            }

    async def read_coils(self) -> Dict[str, Any]:
        """
        DO0..DO5 röle çıkış durumlarını okur.
        """
        async with self._lock:
            return {
                "barrier_open_relay": self.state.do[0],
                "barrier_close_relay": self.state.do[1],
                "traffic_light_green": self.state.do[2],
                "traffic_light_red": self.state.do[3],
                "siren_active": self.state.do[4],
                "raw_coils": dict(self.state.do)
            }

    async def pulse_barrier_open(
        self,
        duration_ms: int = 800,
        operator: str = "ANPR_AUTO",
        reason: str = "Nizamiye Araç Kabulü"
    ) -> Dict[str, Any]:
        """
        Bariyeri açmak için DO0 rölesine belirlenen süre boyunca (ms) kuru kontak darbesi gönderir.
        Ayrıca trafik ışıklarını yeşile çevirir.
        """
        async with self._lock:
            # 1. DO0 (Open Relay) = True
            self.state.do[0] = True
            # Yeşil lamba = True, Kırmızı lamba = False
            self.state.do[2] = True
            self.state.do[3] = False
            
            # Sınır anahtarlarını güncelle
            self.state.di[3] = False # Artık kapalı değil
            self.state.di[2] = True  # Tam açık konuma geçti
            self.state.last_pulse_timestamp = datetime.now()

            logger.info(f"[ADAM-6060] DO0 Pulse Açıldı: {duration_ms}ms (Operatör: {operator}, Sebep: {reason})")

            # Gerçek Modbus soketine yazma (simülasyon değilse)
            if not self.simulation_mode:
                try:
                    await self._modbus_write_coil(0, True)
                except Exception as e:
                    logger.error(f"Modbus DO0 yazma hatası: {e}")

        # Pulse süresi kadar bekle (kuru kontak darbesi)
        await asyncio.sleep(duration_ms / 1000.0)

        async with self._lock:
            # Röle darbesini sonlandır
            self.state.do[0] = False
            if not self.simulation_mode:
                try:
                    await self._modbus_write_coil(0, False)
                except Exception as e:
                    logger.error(f"Modbus DO0 kapatma hatası: {e}")

        return {
            "success": True,
            "action": "OPEN",
            "relay_channel": 0,
            "pulse_duration_ms": duration_ms,
            "safety_photocell_clear": self.state.di[1],
            "loop_detector_active": self.state.di[0],
            "interlock_status": "SAFE_TO_OPERATE",
            "message": f"Bariyer açma rölesi (DO0) {duration_ms}ms darbe ile tetiklendi. Trafik ışığı yeşil.",
            "timestamp": datetime.now()
        }

    async def pulse_barrier_close(
        self,
        duration_ms: int = 800,
        force_override: bool = False
    ) -> Dict[str, Any]:
        """
        Bariyeri kapatmak için DO1 rölesine kontak darbesi gönderir.
        GÜVENLİK KİLİDİ (Interlock): Eğer DI1 (Fotosel) False ise (yani bariyerin altında araç veya cisim varsa),
        sistem işlemi reddeder.
        """
        async with self._lock:
            # Güvenlik Kontrolü
            photocell_safe = self.state.di[1] # True = Güvenli/Temiz
            inbound_loop = self.state.di[0]   # Araç hala döngü üzerinde mi?

            if not photocell_safe and not force_override:
                err_msg = "GÜVENLİK ENGELİ: Bariyer altı güvenlik fotoseli kesilmiş durumda! Kapatma komutu iptal edildi."
                logger.warning(f"[ADAM-6060] {err_msg}")
                raise SafetyInterlockException(err_msg)

            if inbound_loop and not force_override:
                err_msg = "GÜVENLİK ENGELİ: Manyetik loop dedektörü üzerinde araç algılanıyor! Kapatma engellendi."
                logger.warning(f"[ADAM-6060] {err_msg}")
                raise SafetyInterlockException(err_msg)

            # Kapama darbesi
            self.state.do[1] = True
            # Trafik ışıkları: Kırmızı aç, Yeşil kapat
            self.state.do[2] = False
            self.state.do[3] = True
            self.state.di[2] = False # Artık açık değil
            self.state.di[3] = True  # Kapalı konuma geçti

            if not self.simulation_mode:
                try:
                    await self._modbus_write_coil(1, True)
                except Exception as e:
                    logger.error(f"Modbus DO1 yazma hatası: {e}")

        await asyncio.sleep(duration_ms / 1000.0)

        async with self._lock:
            self.state.do[1] = False
            if not self.simulation_mode:
                try:
                    await self._modbus_write_coil(1, False)
                except Exception as e:
                    logger.error(f"Modbus DO1 kapatma hatası: {e}")

        return {
            "success": True,
            "action": "CLOSE",
            "relay_channel": 1,
            "pulse_duration_ms": duration_ms,
            "safety_photocell_clear": self.state.di[1],
            "loop_detector_active": self.state.di[0],
            "interlock_status": "SAFE_TO_OPERATE",
            "message": f"Bariyer kapama rölesi (DO1) {duration_ms}ms darbe ile tetiklendi. Trafik ışığı kırmızı.",
            "timestamp": datetime.now()
        }

    async def emergency_open(self, operator: str = "MANUAL_PANIC") -> Dict[str, Any]:
        """
        Nizamiye veya İtfaiye/Afet acil durumunda bariyeri kilitli açık konuma getirir.
        """
        async with self._lock:
            self.state.do[0] = True
            self.state.do[2] = True  # Yeşil
            self.state.do[3] = False # Kırmızı kapalı
            self.state.do[4] = True  # Siren Açık!
            self.state.di[2] = True
            self.state.di[3] = False
            self.state.di[5] = True  # Emergency input

            logger.critical(f"[ADAM-6060] ACİL DURUM AÇILMASI! (Operatör: {operator})")

        return {
            "success": True,
            "action": "EMERGENCY_OPEN",
            "relay_channel": 0,
            "pulse_duration_ms": 0,
            "safety_photocell_clear": self.state.di[1],
            "loop_detector_active": self.state.di[0],
            "interlock_status": "OVERRIDDEN",
            "message": "Bariyer acil durum modunda sürekli AÇIK konumuna kilitlendi ve siren aktif edildi.",
            "timestamp": datetime.now()
        }

    def simulate_hardware_event(
        self,
        loop_active: Optional[bool] = None,
        photocell_clear: Optional[bool] = None,
        barrier_open: Optional[bool] = None
    ):
        """
        Birim ve entegrasyon testlerinde zemin manyetik loop ve fotosel durumunu simüle etmek için kullanılır.
        """
        if loop_active is not None:
            self.state.di[0] = loop_active
        if photocell_clear is not None:
            self.state.di[1] = photocell_clear
        if barrier_open is not None:
            self.state.di[2] = barrier_open
            self.state.di[3] = not barrier_open

    # ----------------- Pure Python Modbus TCP Fonksiyonları -----------------
    async def _modbus_write_coil(self, coil_addr: int, value: bool):
        """Modbus TCP Function Code 0x05 (Write Single Coil)"""
        tx_id = self._next_tx_id()
        val_bytes = 0xFF00 if value else 0x0000
        # MBAP Header: Transaction ID (2B), Protocol ID 0x0000 (2B), Length 0x0006 (2B), Unit ID 0x01 (1B)
        # PDU: Function Code 0x05 (1B), Coil Address (2B), Value (2B)
        packet = struct.pack(">HHHBBHH", tx_id, 0x0000, 6, 1, 0x05, coil_addr, val_bytes)
        await self._send_modbus_packet(packet)

    async def _modbus_read_inputs(self):
        """Modbus TCP Function Code 0x02 (Read Discrete Inputs 0..5)"""
        tx_id = self._next_tx_id()
        packet = struct.pack(">HHHBBHH", tx_id, 0x0000, 6, 1, 0x02, 0, 6)
        resp = await self._send_modbus_packet(packet)
        if resp and len(resp) >= 10:
            byte_val = resp[9]
            for i in range(6):
                self.state.di[i] = bool((byte_val >> i) & 1)

    async def _send_modbus_packet(self, packet: bytes) -> Optional[bytes]:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=1.5
            )
            writer.write(packet)
            await writer.drain()
            resp = await asyncio.wait_for(reader.read(256), timeout=1.5)
            writer.close()
            await writer.wait_closed()
            return resp
        except Exception as e:
            logger.debug(f"Modbus soket iletişimi ({self.host}:{self.port}) gerçekleştirilemedi: {e}")
            return None

# Global Singleton Controller Örneği
adam6060 = ADAM6060Controller(simulation_mode=True)
