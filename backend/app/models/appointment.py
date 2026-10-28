import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dock_id = Column(String(36), ForeignKey("docks.id"), nullable=True)
    
    # Carrier Corporate Identity
    carrier_name = Column(String(120), nullable=False) # e.g. "Borusan Tedarik Zinciri ve Lojistik A.Ş."
    carrier_tax_id = Column(String(11), nullable=True)  # VKN: 10 haneli
    tio_number = Column(String(30), nullable=True)      # TİO Belge No: TİO-34-1002
    
    # Vehicle & Equipment Details (Drop & Hook)
    vehicle_plate = Column(String(20), nullable=False, index=True) # Çekici Plakası: "34 VR 8902"
    trailer_plate = Column(String(20), nullable=True)              # Dorse Plakası: "34 BRS 102"
    
    # Driver Official Registry (U-ETDS compliant)
    driver_name = Column(String(100), nullable=False)
    driver_phone = Column(String(20), nullable=False)
    driver_tckn = Column(String(11), nullable=True)                # 11 haneli TCKN
    
    # Timestamps & Slot
    slot_start = Column(DateTime, nullable=False, index=True)
    slot_end = Column(DateTime, nullable=False)
    actual_dispatch_time = Column(DateTime, nullable=True)         # Fabrikadan fiili sevk zamanı
    actual_gate_in = Column(DateTime, nullable=True)
    actual_dock_in = Column(DateTime, nullable=True)
    actual_dock_out = Column(DateTime, nullable=True)
    actual_gate_out = Column(DateTime, nullable=True)
    
    # Cargo & Weighbridge (Kantar)
    cargo_type = Column(String(50), default="Kuru Gıda & Ambalaj")
    load_type = Column(String(30), default="PALLET") # PALLET, BULK, REEFER, CHEMICAL, CONTAINER
    estimated_pallets = Column(Integer, default=24)
    pallet_type = Column(String(30), default="EPAL / Euro Palet")
    calculated_duration_minutes = Column(Integer, default=45)
    
    weighbridge_ticket_no = Column(String(50), nullable=True)      # KNT-2026-44102
    weighbridge_gross_kg = Column(Float, nullable=True)            # Brüt: 41.240 kg
    weighbridge_tare_kg = Column(Float, nullable=True)             # Dara: 16.820 kg
    weighbridge_net_kg = Column(Float, nullable=True)              # Net: 24.420 kg
    weighbridge_discrepancy = Column(Boolean, default=False)       # ±%3 yasal fire aşımı
    
    # Cold Chain & Food Safety (HACCP)
    measured_temperature_celsius = Column(Float, nullable=True)    # Frigo kargo sıcaklık ölçümü (°C)
    cold_chain_status = Column(String(30), default="NOT_APPLICABLE") # OPTIMAL, WARNING, BREACH_REJECTED, NOT_APPLICABLE
    
    # ERP & Regulatory
    po_number = Column(String(50), nullable=True)                  # SAP PO: PO-4500891234
    e_waybill_uuid = Column(String(50), nullable=True)             # GİB ETTN: 36 char UUID
    waybill_number = Column(String(50), nullable=True)             # Resmi İrsaliye No
    
    # Status Machine
    # SCHEDULED -> GATE_ARRIVED -> WAITING_LOT -> CALLED -> AT_DOCK -> UNLOADING -> COMPLETED -> DEPARTED | NO_SHOW
    status = Column(String(30), default="SCHEDULED", index=True)
    sla_status = Column(String(30), default="ON_TIME")             # ON_TIME, DELAYED_15M, CRITICAL_DEMURRAGE
    
    # Driver Zero-App Token
    tracking_token = Column(String(32), unique=True, default=lambda: f"RR-{uuid.uuid4().hex[:6].upper()}")
    
    # DocuLog Bridge
    waybill_image_url = Column(String(255), nullable=True)
    doculog_document_id = Column(String(50), nullable=True, index=True)
    doculog_status = Column(String(30), default="PENDING")         # PENDING, PARSED, MATCH_OK, DISCREPANCY
    doculog_summary = Column(Text, nullable=True)
    
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dock = relationship("Dock", back_populates="appointments")
    gate_logs = relationship("GateLog", back_populates="appointment", cascade="all, delete-orphan")
    goods_receipt = relationship("GoodsReceipt", back_populates="appointment", uselist=False, cascade="all, delete-orphan")
