import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=False, unique=True)
    waybill_number = Column(String(50), nullable=True, index=True)
    e_waybill_uuid = Column(String(50), nullable=True) # GİB ETTN
    supplier_vkn = Column(String(20), nullable=True)
    supplier_title = Column(String(150), nullable=True)
    receipt_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # ERP & Regulatory
    sap_movement_code = Column(String(20), default="101") # 101: Sağlam Giriş, 103: Bloke Giriş, 122: Satıcıya İade
    uetds_reference_number = Column(String(50), nullable=True)
    status = Column(String(30), default="DRAFT") # DRAFT, APPROVED, BLOCKED, DISCREPANCY, REJECTED
    measured_temperature_celsius = Column(Float, nullable=True) # Frigo sıcaklık kontrolü
    temperature_compliance_status = Column(String(30), default="COMPLIANT") # COMPLIANT, BREACH_BLOCKED, BREACH_RETURNED
    haccp_protocol_notes = Column(Text, nullable=True)
    warehouse_notes = Column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="goods_receipt")
    items = relationship("GoodsReceiptItem", back_populates="goods_receipt", cascade="all, delete-orphan")

class GoodsReceiptItem(Base):
    __tablename__ = "goods_receipt_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    goods_receipt_id = Column(String(36), ForeignKey("goods_receipts.id"), nullable=False)
    line_number = Column(Integer, default=1)
    material_code = Column(String(50), nullable=True)
    description = Column(String(200), nullable=False)
    dispatched_qty = Column(Float, default=0.0)
    received_qty = Column(Float, default=0.0)
    damaged_qty = Column(Float, default=0.0)
    missing_qty = Column(Float, default=0.0)
    uom = Column(String(20), default="ADET") # ADET, PALET, KOLI, KG, TON
    inspection_status = Column(String(30), default="OK") # OK, DAMAGED, MISSING, BLOCKED

    goods_receipt = relationship("GoodsReceipt", back_populates="items")
