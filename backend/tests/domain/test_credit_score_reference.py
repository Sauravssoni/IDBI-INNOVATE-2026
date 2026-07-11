from decimal import Decimal
from app.core.scoring.scorer import ScoringEngine

CANONICAL_PILLARS = [
    "liquidity",
    "cash_flow_capacity",
    "revenue_stability_momentum",
    "repayment_burden_discipline",
    "compliance_formalisation",
    "concentration_resilience",
]


def test_fhi_and_credit_score_perfect_verified_case():
    features = {
        "monthly_revenue_inr": "1000000",
        "monthly_expenses_inr": "500000",
        "consent_status": "VALID",
        "ebitda_monthly": "300000",
        "bank_metrics": {
            "dscr": "2.2",
            "operating_inflows_monthly": "1000000",
            "operating_outflows_monthly": "500000",
        },
        "gst_metrics": {
            "months_filed": 12,
            "avg_monthly_revenue": "1000000",
            "revenue_cv": "0.05",
            "trend": "GROWING",
        },
        "reconciliation_metrics": {"gst_bank_ratio": "1.00"},
        "working_capital_metrics": {"operating_cycle_days": "20"},
        "invoice_metrics": {"top_buyer_concentration": "0.20"},
        "obligation_verification_state": "VERIFIED_ZERO_DEBT",
        "verified_existing_debt_service_monthly": "0",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert (
        fhi_data["financial_health_index"] == Decimal("100.00")
        or fhi_data["financial_health_index"] == 100.0
    )
    assert fhi_data["vyapar_credit_health_score"] == 900
    assert "not a bureau score" in fhi_data["credit_health_disclaimer"]
    assert fhi_data["assessment_certainty"] == "HIGH_CERTAINTY"
    assert fhi_data["score_range"] == {
        "lower": 885,
        "upper": 900,
        "basis": "evidence-conditioned assessment range; not a statistical confidence interval",
    }

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in CANONICAL_PILLARS:
        assert pillar in breakdown
        assert breakdown[pillar]["score"] == breakdown[pillar]["maximum_score"]
        assert breakdown[pillar]["status"] == "VERIFIED"


def test_fhi_and_credit_score_missing_data_abstention():
    features = {}
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert fhi_data["financial_health_index"] is None
    assert fhi_data["vyapar_credit_health_score"] is None
    assert fhi_data["assessment_certainty"] == "INSUFFICIENT_TO_ASSESS"
    assert fhi_data["score_range"] is None

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in CANONICAL_PILLARS:
        assert pillar in breakdown
        assert breakdown[pillar]["score"] is None


def test_fhi_and_credit_score_intermediate_values():
    features = {
        "monthly_revenue_inr": "1000000",
        "monthly_expenses_inr": "850000",
        "ebitda_monthly": "100000",
        "consent_status": "VALID",
        "bank_metrics": {
            "dscr": "1.30",
            "operating_inflows_monthly": "1000000",
            "operating_outflows_monthly": "900000",
        },
        "gst_metrics": {
            "months_filed": 12,
            "avg_monthly_revenue": "1000000",
            "revenue_cv": "0.18",
            "trend": "STABLE",
        },
        "reconciliation_metrics": {"gst_bank_ratio": "0.92"},
        "working_capital_metrics": {"operating_cycle_days": "65"},
        "invoice_metrics": {"top_buyer_concentration": "0.45"},
        "obligation_verification_state": "VERIFIED_OBLIGATIONS",
        "verified_existing_debt_service_monthly": "25000",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert fhi_data["vyapar_credit_health_score"] == 726
    assert float(fhi_data["financial_health_index"]) == 71.00

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in CANONICAL_PILLARS:
        assert pillar in breakdown


def test_missing_reconciliation_and_concentration_do_not_earn_points():
    features = {
        "consent_status": "VALID",
        "monthly_revenue_inr": "1000000",
        "bank_metrics": {
            "dscr": "1.50",
            "operating_inflows_monthly": "1000000",
            "operating_outflows_monthly": "700000",
        },
        "gst_metrics": {
            "months_filed": 12,
            "avg_monthly_revenue": "1000000",
            "revenue_cv": "0.08",
            "trend": "STABLE",
        },
        "obligation_verification_state": "VERIFIED_OBLIGATIONS",
        "verified_existing_debt_service_monthly": "100000",
    }

    fhi_data = ScoringEngine(features).compute_fhi_and_credit_score()

    assert fhi_data["financial_health_index"] is not None
    assert fhi_data["fhi_breakdown"]["compliance_formalisation"]["score"] is None
    assert fhi_data["fhi_breakdown"]["concentration_resilience"]["score"] is None


def test_unknown_obligations_abstain_from_score():
    features = {
        "consent_status": "VALID",
        "monthly_revenue_inr": "1000000",
        "bank_metrics": {
            "operating_inflows_monthly": "1000000",
            "operating_outflows_monthly": "700000",
        },
        "gst_metrics": {
            "months_filed": 12,
            "avg_monthly_revenue": "1000000",
            "revenue_cv": "0.08",
            "trend": "STABLE",
        },
        "reconciliation_metrics": {"gst_bank_ratio": "1.00"},
        "working_capital_metrics": {"operating_cycle_days": "45"},
        "invoice_metrics": {"top_buyer_concentration": "0.20"},
        "obligation_verification_state": "UNKNOWN_OBLIGATIONS",
    }

    fhi_data = ScoringEngine(features).compute_fhi_and_credit_score()

    assert fhi_data["financial_health_index"] is None
    assert fhi_data["vyapar_credit_health_score"] is None
    assert (
        "verified_obligations_or_verified_zero_debt"
        in fhi_data["missing_material_evidence"]
    )


def test_generic_verified_without_amount_abstains():
    features = {
        "consent_status": "VALID",
        "monthly_revenue_inr": "1000000",
        "bank_metrics": {
            "operating_inflows_monthly": "1000000",
            "operating_outflows_monthly": "700000",
        },
        "gst_metrics": {
            "months_filed": 12,
            "avg_monthly_revenue": "1000000",
            "revenue_cv": "0.08",
            "trend": "STABLE",
        },
        "reconciliation_metrics": {"gst_bank_ratio": "1.00"},
        "working_capital_metrics": {"operating_cycle_days": "45"},
        "invoice_metrics": {"top_buyer_concentration": "0.20"},
        "obligation_verification_state": "VERIFIED",
    }

    fhi_data = ScoringEngine(features).compute_fhi_and_credit_score()

    assert fhi_data["assessment_certainty"] == "INSUFFICIENT_TO_ASSESS"
    assert fhi_data["financial_health_index"] is None
