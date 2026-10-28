import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class GateLog(Base):
    __tablename__ = "gate_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=True)
    event_type = Column(String(50), nullable=False) # GATE_IN, OVERRIDE_PLATE, CALL_TO_DOCK, DOCK_IN, UNLOAD_START, UNLOAD_END, GATE_OUT
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    gate_operator = Column(String(50), default="Nizamiye-01")
    override_reason = Column(String(255), nullable=True)
    override_photo_url = Column(String(255), nullable=True)
    idempotency_key = Column(String(64), nullable=True, unique=True, index=True)
    notes = Column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="gate_logs")
