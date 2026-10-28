from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SimulationTickRequest(BaseModel):
    steps: Optional[int] = Field(default=1, description="Çalıştırılacak simülasyon adımı sayısı")
    force_spawn: Optional[bool] = Field(default=False, description="Zorunlu olarak yeni bir Türk lojistik tırı kapıya getir")

class SimulationToggleRequest(BaseModel):
    enabled: Optional[bool] = Field(default=None, description="Simülasyon arka plan görevini başlat/durdur (boş bırakılırsa tersine çevirir)")
    interval_seconds: Optional[float] = Field(default=None, ge=0.5, le=60.0, description="Döngü periyodu (saniye)")
    chaos_mode: Optional[bool] = Field(default=None, description="Kaos modu (kantar fire aşımı, acil soğuk zincir sapması, vb.)")
    auto_spawn: Optional[bool] = Field(default=None, description="Otomatik yeni tır akışı")

class TruckInjectionRequest(BaseModel):
    vehicle_plate: Optional[str] = Field(default=None, description="Çekici plakası (Örn: 34 BRS 890)")
    carrier_name: Optional[str] = Field(default=None, description="Lojistik taşıyıcı firma (Borusan, Ekol, Mars, Sütaş Frigo, BİM Dağıtım, Netlog Soğuk Zincir, Horoz Lojistik)")
    load_type: Optional[str] = Field(default="PALLET", description="Yük tipi: PALLET, REEFER, BULK, CHEMICAL, CONTAINER")
    cargo_type: Optional[str] = Field(default=None, description="Yük içeriği açıklaması")
    estimated_pallets: Optional[int] = Field(default=None, ge=1, le=36, description="Tahmini palet sayısı")
    driver_name: Optional[str] = Field(default=None, description="Şoför adı soyadı")
    driver_phone: Optional[str] = Field(default=None, description="Şoför telefon numarası")
    priority: Optional[str] = Field(default="NORMAL", description="Öncelik sınıfı: NORMAL, URGENT_COLD_CHAIN, VIP")
    force_discrepancy: Optional[bool] = Field(default=False, description="Kantar tartımında %3 üzeri fire sapması oluştur")
