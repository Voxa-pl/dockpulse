import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True, default=40.8524)
    longitude = Column(Float, nullable=True, default=29.3812)
    geofence_radius_meters = Column(Integer, default=500)
    timezone = Column(String(50), default="Europe/Istanbul")
    default_quantum_minutes = Column(Integer, default=15)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    docks = relationship("Dock", back_populates="facility", cascade="all, delete-orphan")
