import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from app.db.orm.cases import Business, Case, CaseStatus
from app.db.orm.consents import Consent, DataConnection, ConsentStatus
from app.db.orm.evidence import (
    GSTPeriod,
    BankTransaction,
    Invoice,
    InvoicePayment,
    EmploymentPeriod,
    Obligation,
)
from app.db.orm.users import User
from app.db.orm.org import (
    Branch,
    ProductType,
)

import os
import sys
from sqlalchemy import text


def seed_shakti(db_session=None):
    if db_session is None:
        from app.db.session import SessionLocal

        db = SessionLocal()
    else:
        db = db_session
    if db_session is None:
        from app.db.session import SessionLocal
    else:
        db = db_session
    if (
        os.environ.get("APP_ENV") == "production"
        and os.environ.get("DEMO_ACCESS_ENABLED", "false").lower() != "true"
    ):
        print("Demo seeding is refused in production.")
        sys.exit(1)

    try:
        # Clean previous data to be idempotent
        existing_business = (
            db.query(Business)
            .filter(Business.business_id == "SHAKTI_PRECISION_001")
            .first()
        )
        if existing_business:
            db.query(GSTPeriod).filter(
                GSTPeriod.business_id_fk == existing_business.id
            ).delete()
            db.query(BankTransaction).filter(
                BankTransaction.business_id_fk == existing_business.id
            ).delete()

            invoices = (
                db.query(Invoice)
                .filter(Invoice.business_id_fk == existing_business.id)
                .all()
            )
            for inv in invoices:
                db.query(InvoicePayment).filter(
                    InvoicePayment.invoice_id_fk == inv.id
                ).delete()
            db.query(Invoice).filter(
                Invoice.business_id_fk == existing_business.id
            ).delete()

            db.query(Obligation).filter(
                Obligation.business_id_fk == existing_business.id
            ).delete()
            db.query(EmploymentPeriod).filter(
                EmploymentPeriod.business_id_fk == existing_business.id
            ).delete()
            db.query(Consent).filter(
                Consent.business_id_fk == existing_business.id
            ).delete()
            db.query(DataConnection).filter(
                DataConnection.business_id_fk == existing_business.id
            ).delete()

            # Delete audit events for the case
            case = (
                db.query(Case)
                .filter(Case.business_id_fk == existing_business.id)
                .first()
            )
            if case:
                db.execute(
                    text("DELETE FROM audit_events WHERE case_id = :case_id"),
                    {"case_id": case.id},
                )
                db.execute(
                    text("DELETE FROM idempotency_records WHERE case_id = :case_id"),
                    {"case_id": case.id},
                )
            db.query(Case).filter(Case.business_id_fk == existing_business.id).delete()
            db.query(Business).filter(Business.id == existing_business.id).delete()
            db.commit()

        malviya_nagar_branch = (
            db.query(Branch).filter(Branch.code == "BR-MN-JAI").first()
        )
        if not malviya_nagar_branch:
            from app.seed.seed_demo_principals import seed_demo_principals

            seed_demo_principals(db)
            malviya_nagar_branch = (
                db.query(Branch).filter(Branch.code == "BR-MN-JAI").first()
            )

        rm_user = db.query(User).filter(User.email == "rm@bank.example").first()
        ca_user = db.query(User).filter(User.email == "credit@bank.example").first()
        sa_user = db.query(User).filter(User.email == "sa@bank.example").first()
        if not rm_user or not ca_user or not sa_user:
            from app.seed.seed_demo_principals import seed_demo_principals

            seed_demo_principals(db)
            rm_user = db.query(User).filter(User.email == "rm@bank.example").first()
            ca_user = db.query(User).filter(User.email == "credit@bank.example").first()
            sa_user = db.query(User).filter(User.email == "sa@bank.example").first()

        # Seed deterministic random for reproducibility
        random.seed(42)

        # 2. Create Business
        shakti = Business(
            business_id="SHAKTI_PRECISION_001",
            legal_name="Shakti Precision Components Pvt Ltd",
            sector="Manufacturing - Auto Ancillary",
        )
        db.add(shakti)
        db.flush()
        db.refresh(shakti)

        # 3. Create Consents & Connections
        today = date(2026, 7, 1)

        sources = ["GST", "ACCOUNT_AGGREGATOR", "EPFO", "UPI", "CIBIL"]
        consents_by_source = {}
        connections_by_source = {}
        for source in sources:
            c = Consent(
                business_id_fk=shakti.id,
                source_type=source,
                status=ConsentStatus.ACTIVE,
                valid_until=today + timedelta(days=90),
            )
            db.add(c)
            d = DataConnection(
                business_id_fk=shakti.id,
                source_type=source,
                status="CONNECTED",
                last_sync_at=today,
            )
            db.add(d)
            db.flush()
            consents_by_source[source] = c.id
            connections_by_source[source] = d.id
        db.flush()

        # 4. Generate 18 months of deterministic data
        start_date = today - relativedelta(months=18)
        base_revenue = Decimal("1477000.00")

        for m in range(18):
            current_month = start_date + relativedelta(months=m)
            month_start = date(current_month.year, current_month.month, 1)

            fluctuation = Decimal(str(round(1.0 + random.uniform(-0.15, 0.15), 4)))  # nosec B311
            monthly_rev = round(base_revenue * fluctuation, 2)

            # GST
            db.add(
                GSTPeriod(
                    business_id_fk=shakti.id,
                    period_month=month_start,
                    declared_revenue=monthly_rev,
                    tax_paid=round(monthly_rev * Decimal("0.18"), 2),
                    source_system="GSTN",
                    source_record_id=f"GST-{m}-{shakti.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["GST"],
                    data_connection_id_fk=connections_by_source["GST"],
                )
            )

            # Bank
            bank_credits = round(
                monthly_rev * Decimal(str(round(random.uniform(0.95, 1.02), 4))),
                2,  # nosec B311
            )
            db.add(
                BankTransaction(
                    business_id_fk=shakti.id,
                    transaction_date=month_start + timedelta(days=5),
                    amount=bank_credits,
                    transaction_type="CREDIT",
                    category="BUYER_RECEIPT",
                    source_system="ACCOUNT_AGGREGATOR",
                    source_record_id=f"TXN-CR-{m}-{shakti.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                    data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
                )
            )

            supplier_payment = round(monthly_rev * Decimal("0.55"), 2)
            db.add(
                BankTransaction(
                    business_id_fk=shakti.id,
                    transaction_date=month_start + timedelta(days=10),
                    amount=supplier_payment,
                    transaction_type="DEBIT",
                    category="SUPPLIER_PAYMENT",
                    source_system="ACCOUNT_AGGREGATOR",
                    source_record_id=f"TXN-SUP-{m}-{shakti.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                    data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
                )
            )

            salary_payment = round(monthly_rev * Decimal("0.15"), 2)
            db.add(
                BankTransaction(
                    business_id_fk=shakti.id,
                    transaction_date=month_start + timedelta(days=1),
                    amount=salary_payment,
                    transaction_type="DEBIT",
                    category="SALARY",
                    source_system="ACCOUNT_AGGREGATOR",
                    source_record_id=f"TXN-SAL-{m}-{shakti.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                    data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
                )
            )

            # EPFO
            db.add(
                EmploymentPeriod(
                    business_id_fk=shakti.id,
                    period_month=month_start,
                    employee_count=int(25 + random.uniform(-2, 3)),  # nosec B311
                    total_pf_remittance=round(salary_payment * Decimal("0.12"), 2),
                    source_system="EPFO",
                    source_record_id=f"EPFO-{m}-{shakti.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["EPFO"],
                    data_connection_id_fk=connections_by_source["EPFO"],
                )
            )

            # Debt Service
            db.add(
                BankTransaction(
                    business_id_fk=shakti.id,
                    transaction_date=month_start + timedelta(days=20),
                    amount=Decimal("228238.12"),
                    transaction_type="DEBIT",
                    category="DEBT_SERVICE",
                    source_system="ACCOUNT_AGGREGATOR",
                    source_record_id=f"TXN-DEBT-{m}-{shakti.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                    data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
                )
            )

        # Invoices
        buyers = ["Tata Motors Ltd", "Mahindra & Mahindra Ltd", "Local Auto Parts"]
        for m in range(18):
            current_month = start_date + relativedelta(months=m)
            month_start = date(current_month.year, current_month.month, 1)

            fluctuation = Decimal(str(round(1.0 + random.uniform(-0.15, 0.15), 4)))  # nosec B311
            monthly_rev = round(base_revenue * fluctuation, 2)

            inv1 = round(monthly_rev * Decimal("0.50"), 2)
            inv2 = round(monthly_rev * Decimal("0.30"), 2)
            inv3 = round(monthly_rev * Decimal("0.20"), 2)

            for idx, amount in enumerate([inv1, inv2, inv3]):
                invoice_date = month_start + timedelta(days=random.randint(1, 15))  # nosec B311
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
                        source_record_id=f"INV-P-{m}-{idx}-{shakti.id}",
                        ingestion_mode="SEEDED_PROTOTYPE",
                        consent_id_fk=consents_by_source["GST"],
                        data_connection_id_fk=connections_by_source["GST"],
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
                        source_record_id=f"INV-D-{m}-{idx}-{shakti.id}",
                        ingestion_mode="SEEDED_PROTOTYPE",
                        consent_id_fk=consents_by_source["GST"],
                        data_connection_id_fk=connections_by_source["GST"],
                    )
                    db.add(inv)
                    db.flush()  # flush to get id

                    settlement = due_date + timedelta(days=random.randint(-5, 15))  # nosec B311
                    db.add(
                        InvoicePayment(
                            invoice_id_fk=inv.id,
                            settlement_date=settlement,
                            amount=amount,
                            source_system="ACCOUNT_AGGREGATOR",
                            source_record_id=f"PAY-{m}-{idx}-{shakti.id}",
                            ingestion_mode="SEEDED_PROTOTYPE",
                            consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                            data_connection_id_fk=connections_by_source[
                                "ACCOUNT_AGGREGATOR"
                            ],
                        )
                    )

        db.add(
            Obligation(
                business_id_fk=shakti.id,
                facility_type="TERM_LOAN",
                monthly_emi=Decimal("228238.12"),
                outstanding_balance=Decimal("8000000.00"),
                source_system="CIBIL",
                source_record_id=f"OBL-1-{shakti.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["CIBIL"],
                data_connection_id_fk=connections_by_source["CIBIL"],
            )
        )

        db.flush()

        # 5. Create Case
        case = Case(
            business_id_fk=shakti.id,
            requested_product=ProductType.WORKING_CAPITAL_LINE,
            requested_amount=Decimal("5000000.00"),
            monthly_revenue_inr=Decimal("1477000.00"),
            currency="INR",
            status=CaseStatus.INITIATED,
            originating_branch_id=malviya_nagar_branch.id,
            assigned_relationship_manager_id=rm_user.id,
            assigned_credit_analyst_id=ca_user.id,
            assigned_sanctioning_authority_id=sa_user.id,
        )
        db.add(case)
        db.commit()

        print(
            f"✅ Successfully seeded Shakti Precision Components (ID: {shakti.id}) and its case."
        )
    finally:
        if db_session is None:
            db.close()


if __name__ == "__main__":
    seed_shakti()
