import uuid
from datetime import date
from sqlalchemy import Column, String, ForeignKey, Date, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base
import enum

class ConsentStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

class Consent(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    source_type = Column(String, nullable=False) # e.g. GST, AA, EPFO
    status = Column(Enum(ConsentStatus), default=ConsentStatus.PENDING, nullable=False)
    valid_until = Column(Date, nullable=False)
    reference_id = Column(String, nullable=True) # external reference ID

    business = relationship("Business")

class DataConnection(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    source_type = Column(String, nullable=False) # e.g. GST, AA, EPFO, UPI
    status = Column(String, nullable=False, default="CONNECTED") # CONNECTED, STALE, FAILED
    last_sync_at = Column(Date, nullable=True)
    last_error = Column(String, nullable=True)

    business = relationship("Business")
