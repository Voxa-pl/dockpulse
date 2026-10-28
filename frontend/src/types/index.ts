export type AppointmentStatus = 
  | 'SCHEDULED' 
  | 'GATE_ARRIVED' 
  | 'WAITING_LOT' 
  | 'CALLED' 
  | 'AT_DOCK' 
  | 'UNLOADING' 
  | 'COMPLETED' 
  | 'DEPARTED' 
  | 'NO_SHOW';

export type SlaStatus = 'ON_TIME' | 'DELAYED_15M' | 'CRITICAL_DEMURRAGE';

export type DockStatus = 'IDLE' | 'RESERVED' | 'CALLING' | 'OCCUPIED' | 'MAINTENANCE';

export type DockType = 'SHELTER' | 'HYDRAULIC' | 'COLD_REEFER' | 'GROUND';

export interface Facility {
  id: string;
  code: string;
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  geofence_radius_meters: number;
  timezone: string;
  default_quantum_minutes: number;
  created_at?: string;
}

export interface Dock {
  id: string;
  facility_id: string;
  dock_number: string;
  dock_type: DockType;
  is_active: boolean;
  max_pallets: number;
  status: DockStatus;
  notes?: string;
}

export interface Appointment {
  id: string;
  dock_id?: string;
  carrier_name: string;
  carrier_tax_id?: string;
  tio_number?: string;
  
  vehicle_plate: string;
  trailer_plate?: string;
  driver_name: string;
  driver_phone: string;
  driver_tckn?: string;
  
  slot_start: string;
  slot_end: string;
  actual_dispatch_time?: string;
  actual_gate_in?: string;
  actual_dock_in?: string;
  actual_dock_out?: string;
  actual_gate_out?: string;
  
  cargo_type?: string;
  load_type: string;
  estimated_pallets: number;
  pallet_type?: string;
  calculated_duration_minutes: number;
  
  weighbridge_ticket_no?: string;
  weighbridge_gross_kg?: number;
  weighbridge_tare_kg?: number;
  weighbridge_net_kg?: number;
  weighbridge_discrepancy?: boolean;
  
  po_number?: string;
  e_waybill_uuid?: string;
  waybill_number?: string;
  
  status: AppointmentStatus;
  sla_status: SlaStatus;
  tracking_token: string;
  
  doculog_document_id?: string;
  doculog_status?: string;
  doculog_summary?: string;
}

export interface GoodsReceiptItem {
  line_number: number;
  material_code?: string;
  description: string;
  dispatched_qty: number;
  received_qty: number;
  damaged_qty: number;
  missing_qty?: number;
  uom: string;
  inspection_status: string;
  damage_reason?: string;
}

export interface GoodsReceipt {
  waybill_number: string;
  e_waybill_uuid?: string;
  supplier_vkn?: string;
  supplier_title?: string;
  sap_movement_code: string;
  uetds_reference_number?: string;
  warehouse_notes?: string;
  status: string;
  items: GoodsReceiptItem[];
}

export interface OperationLog {
  id: string;
  timestamp: string;
  event_type: string;
  severity: 'info' | 'success' | 'warn' | 'error';
  message: string;
  plate?: string;
  dock?: string;
}
