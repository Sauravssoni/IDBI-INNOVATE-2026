import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from app.db.session import SessionLocal
from app.db.orm.cases import Business, Case, CaseStatus
from app.db.orm.consents import Consent, DataConnection, ConsentStatus
from app.db.orm.evidence import GSTPeriod, BankTransaction, Invoice, InvoicePayment, EmploymentPeriod
from app.db.orm.users import User, UserRole
from app.api.auth import get_password_hash

def seed_shakti():
    db = SessionLocal()
    
    # Seed users
    print("Seeding users...")
    users_to_seed = [
        {"email": "rm@bank.example", "password": "password123", "full_name": "Relationship Manager", "role": UserRole.RELATIONSHIP_MANAGER},  # nosec
        {"email": "credit@bank.example", "password": "password123", "full_name": "Credit Analyst", "role": UserRole.CREDIT_ANALYST},  # nosec
        {"email": "admin@bank.example", "password": "password123", "full_name": "Risk Admin", "role": UserRole.RISK_ADMIN}  # nosec
    ]
    
    for u in users_to_seed:
        existing_user = db.query(User).filter(User.email == u["email"]).first()
        if not existing_user:
            new_user = User(
                email=u["email"],
                hashed_password=get_password_hash(u["password"]),
                full_name=u["full_name"],
                role=u["role"]
            )
            db.add(new_user)
    db.commit()

    # 1. Clear existing Shakti data to make seeding idempotent
    existing_business = db.query(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
    if existing_business:
        db.query(GSTPeriod).filter(GSTPeriod.business_id_fk == existing_business.id).delete()
        db.query(BankTransaction).filter(BankTransaction.business_id_fk == existing_business.id).delete()
        
        # Invoices and Payments
        invoices = db.query(Invoice).filter(Invoice.business_id_fk == existing_business.id).all()
        for inv in invoices:
            db.query(InvoicePayment).filter(InvoicePayment.invoice_id_fk == inv.id).delete()
        db.query(Invoice).filter(Invoice.business_id_fk == existing_business.id).delete()
        
        db.query(EmploymentPeriod).filter(EmploymentPeriod.business_id_fk == existing_business.id).delete()
        db.query(Consent).filter(Consent.business_id_fk == existing_business.id).delete()
        db.query(DataConnection).filter(DataConnection.business_id_fk == existing_business.id).delete()
        
        for c in existing_business.cases:
            from app.db.orm.cases import AuditEvent
            db.query(AuditEvent).filter(AuditEvent.case_id == c.id).delete()
            
        db.query(Case).filter(Case.business_id_fk == existing_business.id).delete()
        db.delete(existing_business)
        db.commit()

    # Seed deterministic random for reproducibility
    random.seed(42)

    # 2. Create Business
    shakti = Business(
        business_id="SHAKTI_PRECISION_001",
        legal_name="Shakti Precision Components Pvt Ltd",
        sector="Manufacturing - Auto Ancillary"
    )
    db.add(shakti)
    db.commit()
    db.refresh(shakti)

    # 3. Create Consents & Connections
    today = date(2026, 7, 1)
    
    sources = ["GST", "ACCOUNT_AGGREGATOR", "EPFO", "UPI"]
    for source in sources:
        db.add(Consent(
            business_id_fk=shakti.id,
            source_type=source,
            status=ConsentStatus.ACTIVE,
            valid_until=today + timedelta(days=90)
        ))
        db.add(DataConnection(
            business_id_fk=shakti.id,
            source_type=source,
            status="CONNECTED",
            last_sync_at=today
        ))
    db.commit()

    # 4. Generate 18 months of deterministic data
    start_date = today - relativedelta(months=18)
    base_revenue = Decimal("1850000.00")
    
    for m in range(18):
        current_month = start_date + relativedelta(months=m)
        month_start = date(current_month.year, current_month.month, 1)
        
        fluctuation = Decimal(str(round(1.0 + random.uniform(-0.15, 0.15), 4)))  # nosec
        monthly_rev = round(base_revenue * fluctuation, 2)
        
        # GST
        db.add(GSTPeriod(
            business_id_fk=shakti.id,
            period_month=month_start,
            declared_revenue=monthly_rev,
            tax_paid=round(monthly_rev * Decimal("0.18"), 2),
            source_system="GSTN",
            source_record_id=f"GST-{m}-{shakti.id}"
        ))
        
        # Bank
        bank_credits = round(monthly_rev * Decimal(str(round(random.uniform(0.95, 1.02), 4))), 2)  # nosec
        db.add(BankTransaction(
            business_id_fk=shakti.id,
            transaction_date=month_start + timedelta(days=5),
            amount=bank_credits,
            transaction_type="CREDIT",
            category="BUYER_RECEIPT",
            source_system="ACCOUNT_AGGREGATOR",
            source_record_id=f"TXN-CR-{m}-{shakti.id}"
        ))
        
        supplier_payment = round(monthly_rev * Decimal("0.55"), 2)
        db.add(BankTransaction(
            business_id_fk=shakti.id,
            transaction_date=month_start + timedelta(days=10),
            amount=supplier_payment,
            transaction_type="DEBIT",
            category="SUPPLIER_PAYMENT",
            source_system="ACCOUNT_AGGREGATOR",
            source_record_id=f"TXN-SUP-{m}-{shakti.id}"
        ))
        
        salary_payment = round(monthly_rev * Decimal("0.15"), 2)
        db.add(BankTransaction(
            business_id_fk=shakti.id,
            transaction_date=month_start + timedelta(days=1),
            amount=salary_payment,
            transaction_type="DEBIT",
            category="SALARY",
            source_system="ACCOUNT_AGGREGATOR",
            source_record_id=f"TXN-SAL-{m}-{shakti.id}"
        ))
        
        # EPFO
        db.add(EmploymentPeriod(
            business_id_fk=shakti.id,
            period_month=month_start,
            employee_count=int(25 + random.uniform(-2, 3)),  # nosec
            total_pf_remittance=round(salary_payment * Decimal("0.12"), 2),
            source_system="EPFO",
            source_record_id=f"EPFO-{m}-{shakti.id}"
        ))

    # Invoices
    buyers = ["Tata Motors Ltd", "Mahindra & Mahindra Ltd", "Local Auto Parts"]
    for m in range(18):
        current_month = start_date + relativedelta(months=m)
        month_start = date(current_month.year, current_month.month, 1)
        
        fluctuation = Decimal(str(round(1.0 + random.uniform(-0.15, 0.15), 4)))  # nosec
        monthly_rev = round(base_revenue * fluctuation, 2)
        
        inv1 = round(monthly_rev * Decimal("0.50"), 2)
        inv2 = round(monthly_rev * Decimal("0.30"), 2)
        inv3 = round(monthly_rev * Decimal("0.20"), 2)
        
        for idx, amount in enumerate([inv1, inv2, inv3]):
            invoice_date = month_start + timedelta(days=random.randint(1, 15))  # nosec
            due_date = invoice_date + timedelta(days=45)
            
            if m >= 16:
                status = "PENDING"
                inv = Invoice(
                    business_id_fk=shakti.id,
                    counterparty_name=buyers[idx],
                    invoice_date=invoice_date,
                    due_date=due_date,
                    amount=amount,
                    status=status,
                    source_system="GST_E_INVOICE",
                    source_record_id=f"INV-P-{m}-{idx}-{shakti.id}"
                )
                db.add(inv)
            else:
                status = "PAID"
                inv = Invoice(
                    business_id_fk=shakti.id,
                    counterparty_name=buyers[idx],
                    invoice_date=invoice_date,
                    due_date=due_date,
                    amount=amount,
                    status=status,
                    source_system="GST_E_INVOICE",
                    source_record_id=f"INV-D-{m}-{idx}-{shakti.id}"
                )
                db.add(inv)
                db.flush() # flush to get id
                
                settlement = due_date + timedelta(days=random.randint(-5, 15))  # nosec
                db.add(InvoicePayment(
                    invoice_id_fk=inv.id,
                    settlement_date=settlement,
                    amount=amount,
                    source_system="ACCOUNT_AGGREGATOR",
                    source_record_id=f"PAY-{m}-{idx}-{shakti.id}"
                ))

    db.commit()

    # 5. Create Case
    case = Case(
        business_id_fk=shakti.id,
        requested_facility_type="Working Capital Term Loan",
        requested_amount=Decimal("5000000.00"),
        status=CaseStatus.INITIATED
    )
    db.add(case)
    db.commit()

    print(f"✅ Successfully seeded Shakti Precision Components (ID: {shakti.id}) and its case.")

if __name__ == "__main__":
    seed_shakti()
