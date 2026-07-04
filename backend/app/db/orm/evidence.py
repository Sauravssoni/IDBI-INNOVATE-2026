import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, Date, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base

def utc_now():
    return datetime.now(timezone.utc)

class EvidenceMetadata:
    """Mixin for common evidence tracking metadata."""
    source_environment = Column(String, nullable=False, default="SANDBOX")
    source_system = Column(String, nullable=False)
    source_record_id = Column(String, nullable=False)
    ingestion_run_id = Column(String, nullable=True)
    schema_version = Column(String, nullable=False, default="1.0")
    evidence_as_of = Column(DateTime, nullable=False, default=utc_now)
    received_at = Column(DateTime, nullable=False, default=utc_now)
    data_quality_status = Column(String, nullable=False, default="VALID")
    provenance_hash = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

class GSTPeriod(Base, EvidenceMetadata):
    __tablename__ = "gst_periods"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    period_month = Column(Date, nullable=False)
    declared_revenue = Column(Numeric(20, 2, asdecimal=True), nullable=False)
    tax_paid = Column(Numeric(20, 2, asdecimal=True), nullable=False)

    business = relationship("Business")

class BankTransaction(Base, EvidenceMetadata):
    __tablename__ = "bank_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    transaction_date = Column(Date, nullable=False)
    amount = Column(Numeric(20, 2, asdecimal=True), nullable=False)
    transaction_type = Column(String, nullable=False) # CREDIT, DEBIT
    category = Column(String, nullable=True)

    business = relationship("Business")

class Invoice(Base, EvidenceMetadata):
    __tablename__ = "invoices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    counterparty_name = Column(String, nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(20, 2, asdecimal=True), nullable=False)
    status = Column(String, nullable=False) # PENDING, PAID, OVERDUE, DISPUTED
    
    business = relationship("Business")
    
class InvoicePayment(Base, EvidenceMetadata):
    __tablename__ = "invoice_payments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id_fk = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    settlement_date = Column(Date, nullable=False)
    amount = Column(Numeric(20, 2, asdecimal=True), nullable=False)
    
    invoice = relationship("Invoice")

class EmploymentPeriod(Base, EvidenceMetadata):
    __tablename__ = "employment_periods"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    period_month = Column(Date, nullable=False)
    employee_count = Column(Integer, nullable=False)
    total_pf_remittance = Column(Numeric(20, 2, asdecimal=True), nullable=False)

    business = relationship("Business")

class Obligation(Base, EvidenceMetadata):
    __tablename__ = "obligations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    facility_type = Column(String, nullable=False)
    monthly_emi = Column(Numeric(20, 2, asdecimal=True), nullable=False)
    outstanding_balance = Column(Numeric(20, 2, asdecimal=True), nullable=False)
    
    business = relationship("Business")
