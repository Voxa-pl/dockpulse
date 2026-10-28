import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Dock(Base):
    __tablename__ = "docks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False)
    dock_number = Column(String(20), nullable=False) # e.g. "Rampa 01", "Rampa 04 (Soğuk)"
    dock_type = Column(String(30), default="SHELTER") # SHELTER, HYDRAULIC, COLD_REEFER, GROUND
    is_active = Column(Boolean, default=True)
    max_pallets = Column(Integer, default=33)
    status = Column(String(30), default="IDLE") # IDLE, RESERVED, CALLING, OCCUPIED, MAINTENANCE
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    facility = relationship("Facility", back_populates="docks")
    appointments = relationship("Appointment", back_populates="dock")
