import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.core.config import settings

class QuantumSlotEngine:
    """
    RampaRandevu 15-Dakikalık Kuantum Tabanlı Dinamik Slot Motoru.
    Formül: T_slot = T_yanaşma + (Palet * T_elleçleme) + T_kontrol + T_buffer
    Çıkan sonuç 15'in katlarına (yukarı) yuvarlanır.
    """

    @classmethod
    def calculate_slot_duration(cls, pallet_count: int, load_type: str = "PALLET") -> int:
        # 1. Yanaşma, körükleme, takozlama
        t_docking = settings.DOCKING_BUFFER_MINUTES # 10 dk
        
        # 2. Elleçleme hızı
        if load_type == "BULK":
            # Dökme/koli yükleme elleçleme daha uzundur
            t_handling = pallet_count * 2.5
        else:
            t_handling = pallet_count * settings.PALLET_HANDLING_MINUTES # Standart palet: 1.2 dk
        
        # 3. Kontrol süresi
        if load_type == "REEFER":
            t_inspection = settings.INSPECTION_REEFER_MINUTES # Soğuk zincir derece kontrolü: 15 dk
        else:
            t_inspection = settings.INSPECTION_DEFAULT_MINUTES # Kuru yük: 5 dk
        
        # 4. Operasyonel tolerans
        t_buffer = 5 # 5 dk
        
        raw_minutes = t_docking + t_handling + t_inspection + t_buffer
        
        # 15 dakikalık kuantuma yukarı yuvarlama
        quantum = settings.QUANTUM_MINUTES # 15
        calculated = math.ceil(raw_minutes / quantum) * quantum
        
        # Minimum 30 dk, Maksimum 180 dk sınırları
        return max(30, min(calculated, 180))

    @classmethod
    def generate_day_slots(cls, start_hour: int = 8, end_hour: int = 20, quantum_minutes: int = 15) -> List[str]:
        slots = []
        current = datetime(2026, 1, 1, start_hour, 0)
        end = datetime(2026, 1, 1, end_hour, 0)
        while current < end:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=quantum_minutes)
        return slots

    @classmethod
    def validate_dock_compatibility(cls, dock_type: str, load_type: str) -> bool:
        if load_type == "REEFER" and dock_type != "COLD_REEFER":
            return False
        if load_type == "BULK" and dock_type == "COLD_REEFER":
            return False
        return True
