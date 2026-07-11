from decimal import Decimal
import pytest
from app.core.scoring.scorer import ScoringEngine

CANONICAL_PILLARS = [
    "operating_resilience",
    "cash_flow_health",
    "margin_stability",
    "working_capital_velocity",
    "gst_compliance",
    "obligation_discipline",
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

    assert float(fhi_data["financial_health_index"]) == 26.67
    assert fhi_data["vyapar_credit_health_score"] == 240

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in CANONICAL_PILLARS:
        assert pillar in breakdown


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

    assert fhi_data["vyapar_credit_health_score"] == 600
    assert float(fhi_data["financial_health_index"]) == 66.67

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in CANONICAL_PILLARS:
        assert pillar in breakdown
