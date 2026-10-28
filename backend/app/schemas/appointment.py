from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class AppointmentBase(BaseModel):
    carrier_name: str
    carrier_tax_id: Optional[str] = None
    tio_number: Optional[str] = None
    
    vehicle_plate: str
    trailer_plate: Optional[str] = None
    driver_name: str
    driver_phone: str
    driver_tckn: Optional[str] = None
    
    slot_start: datetime
    slot_end: Optional[datetime] = None
    dock_id: Optional[str] = None
    
    cargo_type: Optional[str] = "Kuru Gıda & Ambalaj"
    load_type: str = "PALLET"
    estimated_pallets: int = 24
    pallet_type: Optional[str] = "EPAL / Euro Palet"
    
    weighbridge_ticket_no: Optional[str] = None
    weighbridge_gross_kg: Optional[float] = None
    weighbridge_tare_kg: Optional[float] = None
    weighbridge_net_kg: Optional[float] = None
    weighbridge_discrepancy: Optional[bool] = False
    
    # Cold Chain & Food Safety
    measured_temperature_celsius: Optional[float] = None
    cold_chain_status: Optional[str] = "NOT_APPLICABLE"
    
    po_number: Optional[str] = None
    e_waybill_uuid: Optional[str] = None
    waybill_number: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    waybill_image_base64: Optional[str] = None

class AppointmentStatusUpdate(BaseModel):
    status: str
    dock_id: Optional[str] = None
    notes: Optional[str] = None

class CallToDockRequest(BaseModel):
    dock_id: str
    assigned_by: Optional[str] = "Rampa Amiri"

class ItemReceiptDetail(BaseModel):
    line_number: int
    material_code: Optional[str] = None
    description: str
    dispatched_qty: float
    received_qty: float
    damaged_qty: float = 0.0
    missing_qty: float = 0.0
    uom: str = "ADET"
    inspection_status: str = "OK" # OK, DAMAGED, MISSING, BLOCKED
    damage_reason: Optional[str] = None

class GoodsReceiptSave(BaseModel):
    waybill_number: Optional[str] = None
    e_waybill_uuid: Optional[str] = None
    supplier_vkn: Optional[str] = None
    supplier_title: Optional[str] = None
    sap_movement_code: str = "101"
    uetds_reference_number: Optional[str] = None
    warehouse_notes: Optional[str] = None
    measured_temperature_celsius: Optional[float] = None
    temperature_compliance_status: Optional[str] = "COMPLIANT"
    haccp_protocol_notes: Optional[str] = None
    items: List[ItemReceiptDetail] = []

class AppointmentResponse(AppointmentBase):
    id: str
    calculated_duration_minutes: int
    status: str
    sla_status: str
    tracking_token: str
    actual_gate_in: Optional[datetime] = None
    actual_dock_in: Optional[datetime] = None
    actual_dock_out: Optional[datetime] = None
    actual_gate_out: Optional[datetime] = None
    doculog_document_id: Optional[str] = None
    doculog_status: Optional[str] = None
    doculog_summary: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
