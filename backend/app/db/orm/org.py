import uuid
from sqlalchemy import String, ForeignKey, Enum, Numeric, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum


def utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


class ProductType(str, enum.Enum):
    WORKING_CAPITAL_LINE = "WORKING_CAPITAL_LINE"
    RECEIVABLES_FINANCE = "RECEIVABLES_FINANCE"
    TERM_LOAN = "TERM_LOAN"


class Region(Base):
    __tablename__ = "regions"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = mapped_column(String, unique=True, index=True, nullable=False)
    name = mapped_column(String, nullable=False)

    branches = relationship("Branch", back_populates="region")


class Branch(Base):
    __tablename__ = "branches"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = mapped_column(String, unique=True, index=True, nullable=False)
    name = mapped_column(String, nullable=False)
    region_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False
    )

    region = relationship("Region", back_populates="branches")
    cases = relationship("Case", back_populates="originating_branch")


class UserBranchScope(Base):
    __tablename__ = "user_branch_scopes"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    branch_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    scope_role = mapped_column(String, nullable=False, default="PRIMARY")
    can_read = mapped_column(Boolean, nullable=False, default=True)
    can_recommend = mapped_column(Boolean, nullable=False, default=False)
    active = mapped_column(Boolean, nullable=False, default=True)
    valid_from = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until = mapped_column(DateTime(timezone=True), nullable=True)


class SanctioningMandate(Base):
    __tablename__ = "sanctioning_mandates"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    branch_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True
    )
    region_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.id"), nullable=True
    )
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False)
    currency = mapped_column(String, default="INR", nullable=False)
    maximum_amount = mapped_column(Numeric(20, 2), nullable=False)
    active = mapped_column(Boolean, nullable=False, default=True)
    valid_from = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until = mapped_column(DateTime(timezone=True), nullable=True)
    mandate_version = mapped_column(Integer, nullable=False, default=1)
    created_by = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
