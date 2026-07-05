import uuid
from sqlalchemy import String, ForeignKey, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column
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
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = mapped_column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    source_type = mapped_column(String, nullable=False) # e.g. GST, AA, EPFO
    status: Mapped[ConsentStatus] = mapped_column(Enum(ConsentStatus), default=ConsentStatus.PENDING, nullable=False)
    valid_until = mapped_column(Date, nullable=False)
    reference_id = mapped_column(String, nullable=True) # external reference ID

    business = relationship("Business")

class DataConnection(Base):
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = mapped_column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    source_type = mapped_column(String, nullable=False) # e.g. GST, AA, EPFO, UPI
    status = mapped_column(String, nullable=False, default="CONNECTED") # CONNECTED, STALE, FAILED
    last_sync_at = mapped_column(Date, nullable=True)
    last_error = mapped_column(String, nullable=True)

    business = relationship("Business")
