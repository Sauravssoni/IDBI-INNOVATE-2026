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


def seed_nirmaan(db_session=None):
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
        db.query(Business).filter(Business.business_id == "NIRMAAN_INFRA_001").first()
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

    random.seed(103)
    nirmaan = Business(
        business_id="NIRMAAN_INFRA_001",
        legal_name="Nirmaan Infrastructure Services",
        sector="Construction",
    )
    db.add(nirmaan)
    db.commit()
    db.refresh(nirmaan)

    today = date(2026, 7, 1)
    sources = ["GST", "ACCOUNT_AGGREGATOR", "EPFO", "CIBIL"]
    consents_by_source = {}
    connections_by_source = {}
    for source in sources:
        consent = Consent(
            business_id_fk=nirmaan.id,
            source_type=source,
            status=ConsentStatus.EXPIRED,
            valid_until=today - timedelta(days=1),
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)
        consents_by_source[source] = consent.id

        connection = DataConnection(
            business_id_fk=nirmaan.id,
            source_type=source,
            status="CONNECTED",
            last_sync_at=today,
        )
        db.add(connection)
        db.commit()
        connections_by_source[source] = connection.id
    db.commit()

    start_date = today - relativedelta(months=18)
    base_revenue = Decimal("5500000.00")

    for m in range(18):
        current_month = start_date + relativedelta(months=m)
        month_start = date(current_month.year, current_month.month, 1)

        fluctuation = Decimal(str(round(1.0 + random.uniform(-0.1, 0.1), 4)))  # nosec B311
        monthly_rev = round(base_revenue * fluctuation, 2)

        # Huge GST variance
        # GST reports 55L, but Bank gets only 20L for the last 6 months
        if m >= 12:
            gst_revenue = monthly_rev
            bank_credits = round(monthly_rev * Decimal("0.3"), 2)
        else:
            gst_revenue = monthly_rev
            bank_credits = round(
                monthly_rev * Decimal(str(round(random.uniform(0.98, 1.05), 4))), 2  # nosec B311
            )

        db.add(
            GSTPeriod(
                business_id_fk=nirmaan.id,
                period_month=month_start,
                declared_revenue=gst_revenue,
                tax_paid=round(gst_revenue * Decimal("0.18"), 2),
                source_system="GSTN",
                source_record_id=f"GST-{m}-{nirmaan.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["GST"],
                data_connection_id_fk=connections_by_source["GST"],
            )
        )

        db.add(
            BankTransaction(
                business_id_fk=nirmaan.id,
                transaction_date=month_start + timedelta(days=5),
                amount=bank_credits,
                transaction_type="CREDIT",
                category="BUYER_RECEIPT",
                source_system="ACCOUNT_AGGREGATOR",
                source_record_id=f"TXN-CR-{m}-{nirmaan.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
            )
        )
        db.add(
            BankTransaction(
                business_id_fk=nirmaan.id,
                transaction_date=month_start + timedelta(days=10),
                amount=round(monthly_rev * Decimal("0.60"), 2),
                transaction_type="DEBIT",
                category="SUPPLIER_PAYMENT",
                source_system="ACCOUNT_AGGREGATOR",
                source_record_id=f"TXN-SUP-{m}-{nirmaan.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
            )
        )

        db.add(
            EmploymentPeriod(
                business_id_fk=nirmaan.id,
                period_month=month_start,
                employee_count=120,
                total_pf_remittance=round(monthly_rev * Decimal("0.08"), 2),
                source_system="EPFO",
                source_record_id=f"EPFO-{m}-{nirmaan.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["EPFO"],
                data_connection_id_fk=connections_by_source["EPFO"],
            )
        )

        db.add(
            BankTransaction(
                business_id_fk=nirmaan.id,
                transaction_date=month_start + timedelta(days=20),
                amount=Decimal("450000.00"),
                transaction_type="DEBIT",
                category="DEBT_SERVICE",
                source_system="ACCOUNT_AGGREGATOR",
                source_record_id=f"TXN-DEBT-{m}-{nirmaan.id}",
                ingestion_mode="SEEDED_PROTOTYPE",
                consent_id_fk=consents_by_source["ACCOUNT_AGGREGATOR"],
                data_connection_id_fk=connections_by_source["ACCOUNT_AGGREGATOR"],
            )
        )

    db.add(
        Obligation(
            business_id_fk=nirmaan.id,
            facility_type="TERM_LOAN",
            monthly_emi=Decimal("450000.00"),
            outstanding_balance=Decimal("15000000.00"),
            source_system="CIBIL",
            source_record_id=f"OBL-1-{nirmaan.id}",
            ingestion_mode="SEEDED_PROTOTYPE",
            consent_id_fk=consents_by_source["CIBIL"],
            data_connection_id_fk=connections_by_source["CIBIL"],
        )
    )

    db.commit()

    case = Case(
        business_id_fk=nirmaan.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        requested_amount=Decimal("5000000.00"),
        currency="INR",
        status=CaseStatus.INITIATED,
        originating_branch_id=malviya_nagar_branch.id if malviya_nagar_branch else None,
        assigned_relationship_manager_id=rm_user.id if rm_user else None,
        assigned_credit_analyst_id=ca_user.id if ca_user else None,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    return nirmaan.business_id, case.id


if __name__ == "__main__":
    seed_nirmaan()
