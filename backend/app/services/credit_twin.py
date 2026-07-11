from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException

from app.db.orm.cases import Case
from app.db.orm.evidence import BankTransaction, GSTPeriod


def calculate_dscr_sandbox_v1(db: Session, business_id: str, as_of_date: date):
    """
    Trailing 12-month (TTM) DSCR = NOI / Debt Service
    NOI = Operating Inflows - Operating Outflows (governed by category whitelists)
    Debt Service = Debits (DEBT_SERVICE)
    """
    from app.core.features.engine import FeatureEngine

    start_date = as_of_date - relativedelta(months=12)
    txns = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.business_id_fk == business_id,
            BankTransaction.transaction_date >= start_date,
            BankTransaction.transaction_date < as_of_date,
        )
        .all()
    )

    operating_inflows = sum(
        (
            t.amount
            for t in txns
            if t.transaction_type == "CREDIT"
            and (t.category or "").upper()
            in FeatureEngine.TRANSACTION_CATEGORY_WHITELISTS["OPERATING_INFLOWS"]
        ),
        Decimal("0.0"),
    )
    operating_outflows = sum(
        (
            t.amount
            for t in txns
            if t.transaction_type == "DEBIT"
            and (t.category or "").upper()
            in FeatureEngine.TRANSACTION_CATEGORY_WHITELISTS["OPERATING_OUTFLOWS"]
        ),
        Decimal("0.0"),
    )
    debt_service = sum(
        (
            t.amount
            for t in txns
            if t.transaction_type == "DEBIT"
            and (t.category or "").upper() == "DEBT_SERVICE"
        ),
        Decimal("0.0"),
    )

    noi = operating_inflows - operating_outflows

    if debt_service == Decimal("0.0"):
        return None

    return round(noi / debt_service, 2)


def calculate_independent_reamortization_dscr(
    db: Session, business_id: str, as_of_date: date
) -> Decimal | None:
    from app.core.features.engine import FeatureEngine
    from app.db.orm.evidence import Obligation

    # 1. Operating inflows
    start_date = as_of_date - relativedelta(months=12)
    txns = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.business_id_fk == business_id,
            BankTransaction.transaction_date >= start_date,
            BankTransaction.transaction_date < as_of_date,
            BankTransaction.transaction_type == "CREDIT",
        )
        .all()
    )
    operating_inflows = sum(
        (
            t.amount
            for t in txns
            if (t.category or "").upper()
            in FeatureEngine.TRANSACTION_CATEGORY_WHITELISTS["OPERATING_INFLOWS"]
        ),
        Decimal("0.0"),
    )
    operating_inflows_monthly = operating_inflows / Decimal("12.0")

    # 2. Verified active obligations
    active_obligations = (
        db.query(Obligation).filter(Obligation.business_id_fk == business_id).all()
    )
    monthly_emi_total = sum(
        (ob.monthly_emi for ob in active_obligations), Decimal("0.0")
    )

    # 3. Add a hypothetical 20% stress buffer to that EMI total
    stressed_monthly_emi = monthly_emi_total * Decimal("1.2")

    if stressed_monthly_emi == Decimal("0.0"):
        return None

    return operating_inflows_monthly / stressed_monthly_emi


def get_credit_twin(db: Session, case_id: str) -> dict:
    from app.db.orm.cases import AuditEvent

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    business_id = case.business_id_fk

    # We assume 'today' is 2026-07-01 for the demo seeding
    today = date(2026, 7, 1)

    dscr = calculate_dscr_sandbox_v1(db, business_id, today)

    # Calculate Total Annual Revenue (GST)
    start_date = today - relativedelta(months=12)
    gst_periods = (
        db.query(GSTPeriod)
        .filter(
            GSTPeriod.business_id_fk == business_id,
            GSTPeriod.period_month >= start_date,
            GSTPeriod.period_month < today,
        )
        .all()
    )
    total_annual_revenue = sum(
        (p.declared_revenue for p in gst_periods), Decimal("0.0")
    )

    latest_eval = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id, AuditEvent.event_type == "evaluate")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )

    binding_limit = None
    scores = {}
    timestamp = None
    if latest_eval and latest_eval.metadata_json:
        metadata = latest_eval.metadata_json
        if "decision" in metadata and "binding_limit" in metadata["decision"]:
            binding_limit = metadata["decision"]["binding_limit"]
        if "scores" in metadata:
            scores = metadata["scores"]
        timestamp = latest_eval.created_at.isoformat()

    from app.db.orm.evidence import Invoice, EmploymentPeriod, Obligation

    has_gst = len(gst_periods) > 0
    has_bank = (
        db.query(BankTransaction)
        .filter(BankTransaction.business_id_fk == business_id)
        .first()
        is not None
    )
    has_invoices = (
        db.query(Invoice).filter(Invoice.business_id_fk == business_id).first()
        is not None
    )
    has_employment = (
        db.query(EmploymentPeriod)
        .filter(EmploymentPeriod.business_id_fk == business_id)
        .first()
        is not None
    )
    has_obligations = (
        db.query(Obligation).filter(Obligation.business_id_fk == business_id).first()
        is not None
    )

    # Source Coverage Formula:
    # Calculates the breadth of data domains provided by the borrower.
    # 5 domains (GST, Bank, Invoices, Employment, Obligations), each worth 20 points.
    # Max Score = 100
    coverage_points = 0
    if has_gst:
        coverage_points += 20
    if has_bank:
        coverage_points += 20
    if has_invoices:
        coverage_points += 20
    if has_employment:
        coverage_points += 20
    if has_obligations:
        coverage_points += 20

    source_coverage = Decimal(str(coverage_points)) if coverage_points > 0 else None

    # Evidence Confidence Formula:
    # Extracted directly from the core Scoring Engine (evidence_confidence_score).
    # It evaluates the depth of history (e.g., >18 months GST) and volume of corroborating records.
    evidence_confidence = None
    if scores and scores.get("evidence_confidence_score") is not None:
        evidence_confidence = Decimal(str(scores["evidence_confidence_score"]))

    # Reconciliation Quality Formula:
    # Extracted from the Reconciliation Engine, reflecting the percentage of bank receipts
    # that deterministically match with declared GST revenue and invoices.
    from app.services.reconciliation import run_reconciliation

    recon = run_reconciliation(db, str(case_id))
    recon_quality = None
    if (
        recon
        and "reconciliation_match_percent" in recon
        and recon["reconciliation_match_percent"] is not None
    ):
        recon_quality = Decimal(str(recon["reconciliation_match_percent"]))

    return {
        "case_id": str(case_id),
        "business_id": str(business_id),
        "dscr": dscr if dscr is not None else None,
        "independent_reamortization_dscr": calculate_independent_reamortization_dscr(
            db, str(business_id), date.today()
        ),
        "calculation_version": "DSCR_SANDBOX_V1",
        "total_annual_revenue": total_annual_revenue,
        "binding_limit": binding_limit if binding_limit is not None else None,
        "recommendation": case.recommendation.value if case.recommendation else None,
        "source_coverage": source_coverage,
        "evidence_confidence": evidence_confidence,
        "reconciliation_quality": recon_quality,
        "evaluated_at": timestamp,
    }
