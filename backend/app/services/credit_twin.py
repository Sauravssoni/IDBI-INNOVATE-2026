from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException

from app.db.orm.cases import Case
from app.db.orm.evidence import BankTransaction


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

    return Decimal(str(operating_inflows_monthly / stressed_monthly_emi))


def get_credit_twin(db: Session, case_id: str) -> dict:
    from app.services.assessment_service import AssessmentService
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    assessment = AssessmentService.get_latest_assessment(db, case_id)
    if not assessment:
        assessment = AssessmentService.evaluate_case(db, case)

    revenue = Decimal("24000000.00")
    if hasattr(assessment, "feature_snapshot") and assessment.feature_snapshot:
        snap = assessment.feature_snapshot
        if isinstance(snap, dict):
            if snap.get("total_annual_revenue"):
                revenue = Decimal(str(snap["total_annual_revenue"]))
            elif snap.get("annual_revenue"):
                revenue = Decimal(str(snap["annual_revenue"]))
            elif isinstance(snap.get("gst_metrics"), dict) and snap["gst_metrics"].get("total_annual_revenue"):
                revenue = Decimal(str(snap["gst_metrics"]["total_annual_revenue"]))
        elif hasattr(snap, "model_dump"):
            snap_dict = snap.model_dump()
            if snap_dict.get("total_annual_revenue"):
                revenue = Decimal(str(snap_dict["total_annual_revenue"]))
            elif snap_dict.get("annual_revenue"):
                revenue = Decimal(str(snap_dict["annual_revenue"]))

    ev_conf = Decimal("90.0") if assessment.evidence_certainty == "HIGH" else Decimal("75.0")

    return {
        "case_id": str(case.id),
        "business_id": str(case.business_id_fk),
        "dscr": assessment.current_dscr,
        "independent_reamortization_dscr": assessment.post_loan_dscr,
        "calculation_version": assessment.calculation_version,
        "total_annual_revenue": revenue,
        "binding_limit": assessment.supportable_amount,
        "recommendation": assessment.policy_recommendation or (case.recommendation.value if case.recommendation else None),
        "source_coverage": Decimal("100.0"),
        "evidence_confidence": ev_conf,
        "reconciliation_quality": Decimal("100.0"),
        "evaluated_at": assessment.generated_at.isoformat() if assessment.generated_at else None,
        "policy_version": assessment.policy_version,
    }
