from decimal import Decimal
import pytest
from app.core.scoring.scorer import ScoringEngine

CANONICAL_PILLARS = [
    "liquidity", "cash_flow_capacity", "revenue_growth",
    "repayment_burden", "compliance_governance", "concentration_risk",
]


def test_fhi_and_credit_score_perfect_verified_case():
    features = {
        "monthly_revenue_inr": "1000000",
        "monthly_expenses_inr": "500000",
        "ebitda_monthly": "300000",
        "bank_metrics": {"dscr": "2.2", "operating_inflows_monthly": "1000000", "operating_outflows_monthly": "500000"},
        "reconciliation_metrics": {"gst_bank_ratio": "1.01"},
        "working_capital_metrics": {"operating_cycle_days": "20"},
        "obligation_verification_state": "VERIFIED",
        "verified_existing_debt_service_monthly": "0",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert fhi_data["financial_health_index"] == Decimal("100.00") or fhi_data["financial_health_index"] == 100.0
    assert fhi_data["vyapar_credit_health_score"] == 900
    assert "proprietary institutional diagnostic indicators" in fhi_data["credit_health_disclaimer"]
    assert "not constitute an official credit bureau score" in fhi_data["credit_health_disclaimer"]

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in CANONICAL_PILLARS:
        assert pillar in breakdown
        assert breakdown[pillar]["score"] == breakdown[pillar]["max_score"]
        assert breakdown[pillar]["status"] == "VERIFIED"


def test_fhi_and_credit_score_missing_data_abstention():
    features = {}
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert float(fhi_data["financial_health_index"]) == 0.0
    assert fhi_data["vyapar_credit_health_score"] == 300

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in CANONICAL_PILLARS:
        assert pillar in breakdown
        assert breakdown[pillar]["score"] == 0.0
        assert breakdown[pillar]["status"] == "MISSING_DATA"


def test_fhi_and_credit_score_intermediate_values():
    features = {
        "monthly_revenue_inr": "1000000",
        "monthly_expenses_inr": "850000",
        "ebitda_monthly": "100000",
        "bank_metrics": {"dscr": "1.30", "operating_inflows_monthly": "1000000", "operating_outflows_monthly": "900000"},
        "reconciliation_metrics": {"gst_bank_ratio": "0.92"},
        "working_capital_metrics": {"operating_cycle_days": "65"},
        "obligation_verification_state": "VERIFIED",
        "verified_existing_debt_service_monthly": "25000",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert fhi_data["vyapar_credit_health_score"] == 738
    assert float(fhi_data["financial_health_index"]) == 73.0

    breakdown = fhi_data["fhi_breakdown"]
    assert breakdown["liquidity"]["score"] == 12.0
    assert breakdown["cash_flow_capacity"]["score"] == 15.0
    assert breakdown["revenue_growth"]["score"] == 12.0
    assert breakdown["repayment_burden"]["score"] == 20.0
    assert breakdown["compliance_governance"]["score"] == 8.0
    assert breakdown["concentration_risk"]["score"] == 6.0
    for pillar in CANONICAL_PILLARS:
        assert breakdown[pillar]["status"] == "VERIFIED"
