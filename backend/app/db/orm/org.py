import uuid
from sqlalchemy import Column, String, ForeignKey, Enum, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class ProductType(str, enum.Enum):
    WORKING_CAPITAL = "WORKING_CAPITAL"
    TERM_LOAN = "TERM_LOAN"
    OVERDRAFT = "OVERDRAFT"
    TRADE_FINANCE = "TRADE_FINANCE"

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
    region_id = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False)
    
    region = relationship("Region", back_populates="branches")
    cases = relationship("Case", back_populates="originating_branch")

class UserBranchScope(Base):
    __tablename__ = "user_branch_scopes"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    branch_id = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)

class SanctioningMandate(Base):
    __tablename__ = "sanctioning_mandates"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    product: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False)
    max_amount = mapped_column(Numeric(18, 2), nullable=False)
    max_tenor_months = mapped_column(Integer, nullable=False)
    currency = mapped_column(String, default="INR", nullable=False)
