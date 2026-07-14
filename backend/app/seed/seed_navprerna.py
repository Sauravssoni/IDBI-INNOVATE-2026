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


def seed_navprerna(db_session=None):
    if db_session is None:
        from app.db.session import SessionLocal

        db = SessionLocal()
    else:
        db = db_session
    if db_session is None:
        from app.db.session import SessionLocal
    else:
        db = db_session
    existing_business = (
        db.query(Business).filter(Business.business_id == "NAVPRERNA_TECH_001").first()
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
        for c in existing_business.cases:
            from app.db.orm.cases import AuditEvent, IdempotencyRecord

            db.query(AuditEvent).filter(AuditEvent.case_id == c.id).delete()
            db.query(IdempotencyRecord).filter(
                IdempotencyRecord.case_id == c.id
            ).delete()
        db.query(Case).filter(Case.business_id_fk == existing_business.id).delete()
        db.delete(existing_business)
        db.commit()

    malviya_nagar_branch = db.query(Branch).filter(Branch.code == "BR-MN-JAI").first()
    rm_user = db.query(User).filter(User.email == "rm@bank.example").first()
    ca_user = db.query(User).filter(User.email == "credit@bank.example").first()

    random.seed(101)
    navprerna = Business(
        business_id="NAVPRERNA_TECH_001",
        legal_name="Navprerna Tech Solutions",
        sector="IT Services",
    )
    db.add(navprerna)
    db.commit()
    db.refresh(navprerna)

    today = date(2026, 7, 1)
    sources = ["GST", "ACCOUNT_AGGREGATOR", "EPFO", "CIBIL"]
    consents_by_source = {}
    connections_by_source = {}
    for source in sources:
        c = Consent(
            business_id_fk=navprerna.id,
            source_type=source,
            status=ConsentStatus.ACTIVE,
            valid_until=today + timedelta(days=90),
        )
        db.add(c)
        d = DataConnection(
            business_id_fk=navprerna.id,
            source_type=source,
            status="CONNECTED",
            last_sync_at=today,
        )
        db.add(d)
        db.commit()
        consents_by_source[source] = c.id
        connections_by_source[source] = d.id
    db.commit()

    start_date = today - relativedelta(months=18)
    base_revenue = Decimal("900000.00")

    for m in range(18):
        current_month = start_date + relativedelta(months=m)
        month_start = date(current_month.year, current_month.month, 1)

        fluctuation = Decimal(str(round(1.0 + random.uniform(-0.1, 0.1), 4)))  # nosec B311
        monthly_rev = round(base_revenue * fluctuation, 2)

        # Missing GST and EPFO for many months to force low evidence confidence
        skip_evidence = m >= 5

        if not skip_evidence:
            db.add(
                GSTPeriod(
                    business_id_fk=navprerna.id,
                    period_month=month_start,
                    declared_revenue=monthly_rev,
                    tax_paid=round(monthly_rev * Decimal("0.18"), 2),
                    source_system="GSTN",
                    source_record_id=f"GST-{m}-{navprerna.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["GST"],
                    data_connection_id_fk=connections_by_source["GST"],
                )
            )

        bank_credits = round(
            monthly_rev * Decimal(str(round(random.uniform(0.98, 1.05), 4))),
            2,  # nosec B311
        )
        db.add(
            BankTransaction(
                business_id_fk=navprerna.id,
                transaction_date=month_start + timedelta(days=5),
                amount=bank_credits,
                transaction_type="CREDIT",
                category="BUYER_RECEIPT",
                source_system="ACCOUNT_AGGREGATOR",
                source_record_id=f"TXN-CR-{m}-{navprerna.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
            )
        )
        # some debits
        db.add(
            BankTransaction(
                business_id_fk=navprerna.id,
                transaction_date=month_start + timedelta(days=10),
                amount=round(monthly_rev * Decimal("0.60"), 2),
                transaction_type="DEBIT",
                category="SUPPLIER_PAYMENT",
                source_system="ACCOUNT_AGGREGATOR",
                source_record_id=f"TXN-SUP-{m}-{navprerna.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
            )
        )

        if not skip_evidence:
            db.add(
                EmploymentPeriod(
                    business_id_fk=navprerna.id,
                    period_month=month_start,
                    employee_count=10,
                    total_pf_remittance=round(monthly_rev * Decimal("0.05"), 2),
                    source_system="EPFO",
                    source_record_id=f"EPFO-{m}-{navprerna.id}",
                    ingestion_mode="SEEDED_PROTOTYPE",
                    consent_id_fk=consents_by_source["EPFO"],
                    data_connection_id_fk=connections_by_source["EPFO"],
                )
            )

        db.add(
            BankTransaction(
                business_id_fk=navprerna.id,
                transaction_date=month_start + timedelta(days=20),
                amount=Decimal("150000.00"),
                transaction_type="DEBIT",
                category="DEBT_SERVICE",
                source_system="ACCOUNT_AGGREGATOR",
                source_record_id=f"TXN-DEBT-{m}-{navprerna.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
            )
        )

    db.add(
        Obligation(
            business_id_fk=navprerna.id,
            facility_type="TERM_LOAN",
            monthly_emi=Decimal("150000.00"),
            outstanding_balance=Decimal("4000000.00"),
            source_system="CIBIL",
            source_record_id=f"OBL-1-{navprerna.id}",
            ingestion_mode="SEEDED_PROTOTYPE",
            consent_id_fk=consents_by_source["CIBIL"],
            data_connection_id_fk=connections_by_source["CIBIL"],
        )
    )

    db.commit()

    case = Case(
        business_id_fk=navprerna.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        requested_amount=Decimal("3000000.00"),
        currency="INR",
        status=CaseStatus.INITIATED,
        originating_branch_id=malviya_nagar_branch.id,
        assigned_relationship_manager_id=rm_user.id,
        assigned_credit_analyst_id=ca_user.id,
    )
    db.add(case)
    db.commit()


if __name__ == "__main__":
    seed_navprerna()
