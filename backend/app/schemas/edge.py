from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ANPREventRequest(BaseModel):
    vendor: Optional[str] = Field("hikvision", description="Camera vendor: hikvision, dahua, generic")
    device_id: Optional[str] = Field("CAM-GATE-IN-01", description="Camera hardware ID / Lane identifier")
    raw_payload: Optional[str] = Field(None, description="Raw XML or JSON string received from camera webhook")
    plate_number: Optional[str] = Field(None, description="Extracted or direct plate number, e.g. '34 VR 8902'")
    confidence: Optional[float] = Field(95.0, description="OCR confidence score (0-100)")
    direction: Optional[str] = Field("ENTRY", description="ENTRY or EXIT")
    image_base64: Optional[str] = Field(None, description="Base64 encoded vehicle or plate snapshot")
    auto_open_barrier: Optional[bool] = Field(True, description="Whether to trigger ADAM-6060 relay DO0 automatically if authorized")
    operator: Optional[str] = Field("IoT-Edge-ANPR", description="Triggering operator or service")
    idempotency_key: Optional[str] = Field(None, description="Unique event ID to prevent duplicate barrier pulses")
    capture_time: Optional[datetime] = Field(None, description="Camera timestamp")

class ANPREventResponse(BaseModel):
    success: bool
    status: str # VERIFIED_SCHEDULED, VERIFIED_WAITING_LOT, ALREADY_IN_YARD, UNAUTHORIZED, NO_APPOINTMENT_FOUND, OFFLINE_AUTHORIZED
    detected_plate: str
    normalized_plate: str
    confidence: float
    camera_vendor: str
    appointment_id: Optional[str] = None
    carrier_name: Optional[str] = None
    driver_name: Optional[str] = None
    assigned_dock: Optional[str] = None
    barrier_action: str # BARRIER_PULSED, BARRIER_KEPT_CLOSED, BARRIER_MANUAL_REQUIRED
    relay_command_sent: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class WeighbridgeRequest(BaseModel):
    indicator_vendor: Optional[str] = Field("baykon", description="Weighbridge indicator model: baykon, esit, tunaylar, generic")
    raw_ascii_data: Optional[str] = Field(None, description="Raw ASCII string read from RS232/RS485 serial port")
    plate_number: Optional[str] = Field(None, description="Vehicle plate to match appointment")
    appointment_id: Optional[str] = Field(None, description="Specific appointment ID")
    weight_kg: Optional[float] = Field(None, description="Weight in kg if already pre-parsed")
    weighing_type: Optional[str] = Field("AUTO", description="FIRST_WEIGHING (Entry), SECOND_WEIGHING (Exit), GROSS, TARE, AUTO")
    ticket_number: Optional[str] = Field(None, description="Weighbridge ticket number (e.g. KNT-2026-44102)")
    scale_id: Optional[str] = Field("SCALE-01", description="Weighbridge scale identifier")
    operator: Optional[str] = Field("Kantar-Operator-01", description="Operator username or automated service")
    expected_net_kg: Optional[float] = Field(None, description="Expected cargo weight for tolerance cross-check")
    steer_axle_kg: Optional[float] = Field(None, description="Ön yönlendirme aksı ağırlığı (kg)")
    drive_axle_kg: Optional[float] = Field(None, description="Çeker aks ağırlığı (kg - Limit: 11.500 kg)")
    trailer_tridem_kg: Optional[float] = Field(None, description="Yarı römork 3'lü dingil grubu ağırlığı (kg)")

class WeighbridgeResponse(BaseModel):
    success: bool
    appointment_id: Optional[str] = None
    vehicle_plate: Optional[str] = None
    indicator_vendor: str
    ticket_number: str
    scale_id: str
    gross_kg: Optional[float] = None
    tare_kg: Optional[float] = None
    net_kg: Optional[float] = None
    is_stable: bool
    unit: str = "kg"
    weighing_type: str
    within_tolerance: bool
    discrepancy_percentage: Optional[float] = None
    tolerance_limit_percent: float = 3.0
    discrepancy_warning: Optional[str] = None
    # Aks Ağırlığı ve Karayolları Denetimi
    steer_axle_kg: Optional[float] = None
    drive_axle_kg: Optional[float] = None
    trailer_tridem_kg: Optional[float] = None
    axle_overloaded: bool = False
    axle_compliance_report: Optional[str] = None
    rebalance_recommendation: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class BarrierPulseRequest(BaseModel):
    gate_id: Optional[str] = Field("GATE_01_IN", description="Gate ID, e.g. GATE_01_IN or GATE_01_OUT")
    action: Optional[str] = Field("OPEN", description="OPEN, CLOSE, EMERGENCY_OPEN, STOP")
    pulse_duration_ms: Optional[int] = Field(800, description="Duration in ms for ADAM-6060 relay contact pulse")
    trigger_source: Optional[str] = Field("EDGE_ANPR", description="Trigger source: EDGE_ANPR, OPERATOR_UI, SAFETY_LOOP, EMERGENCY")
    operator: Optional[str] = Field("IoT-ADAM6060", description="Triggering operator")
    reason: Optional[str] = Field("Bariyer röle tetiklemesi", description="Reason for pulse")
    force_override: Optional[bool] = Field(False, description="Bypass safety interlocks (Emergency only)")

class BarrierPulseResponse(BaseModel):
    success: bool
    gate_id: str
    action: str
    relay_channel: int
    pulse_duration_ms: int
    safety_photocell_clear: bool
    loop_detector_active: bool
    interlock_status: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class DeviceTelemetryItem(BaseModel):
    name: str
    device_type: str
    status: str # ONLINE, OFFLINE, WARNING
    ip_or_port: str
    details: Dict[str, Any] = Field(default_factory=dict)
    last_communication: datetime = Field(default_factory=datetime.now)

class EdgeStatusResponse(BaseModel):
    gateway_id: str
    overall_status: str # ONLINE, DEGRADED, OFFLINE
    wan_connected: bool
    edge_mode: str # STANDALONE_EDGE or CLOUD_CONNECTED
    offline_store_and_forward: Dict[str, Any]
    cameras: Dict[str, Any]
    weighbridge: Dict[str, Any]
    barrier_controller: Dict[str, Any]
    magnetic_loops: Dict[str, Any]
    system_metrics: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class SyncOfflineQueueRequest(BaseModel):
    limit: Optional[int] = Field(100, description="Max records to sync in this batch")

class SyncOfflineQueueResponse(BaseModel):
    processed_count: int
    synced_count: int
    failed_count: int
    remaining_pending: int
    errors: List[str] = Field(default_factory=list)
