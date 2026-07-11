from decimal import Decimal
import pytest
from app.core.scoring.scorer import ScoringEngine

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

    assert fhi_data["financial_health_index"] == Decimal("100.00")
    assert fhi_data["vyapar_credit_health_score"] == 900
    assert "proprietary institutional diagnostic indicators" in fhi_data["credit_health_disclaimer"]
    assert "not constitute an official credit bureau score" in fhi_data["credit_health_disclaimer"]

    breakdown = fhi_data["fhi_breakdown"]
    for pillar in ["operating_resilience", "cash_flow_health", "margin_stability", "working_capital_velocity", "gst_compliance", "obligation_discipline"]:
        assert breakdown[pillar]["score"] == 150.0
        assert breakdown[pillar]["status"] == "VERIFIED"


def test_fhi_and_credit_score_missing_data_abstention():
    features = {}
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert fhi_data["financial_health_index"] == Decimal("26.67")
    assert fhi_data["vyapar_credit_health_score"] == 240

    breakdown = fhi_data["fhi_breakdown"]
    assert breakdown["operating_resilience"]["score"] == 0.0
    assert breakdown["operating_resilience"]["status"] == "MISSING_DATA"
    assert breakdown["working_capital_velocity"]["score"] == 60.0
    assert breakdown["working_capital_velocity"]["status"] == "IMPUTED"
    assert breakdown["gst_compliance"]["score"] == 60.0
    assert breakdown["gst_compliance"]["status"] == "MISSING_DATA"
    assert breakdown["obligation_discipline"]["score"] == 120.0
    assert breakdown["obligation_discipline"]["status"] == "VERIFIED"


def test_fhi_and_credit_score_intermediate_values():
    features = {
        "monthly_revenue_inr": "1000000",
        "monthly_expenses_inr": "850000", # margin 0.15 -> 120
        "ebitda_monthly": "100000", # npm 0.10 -> 120
        "bank_metrics": {"dscr": "1.30", "operating_inflows_monthly": "1000000", "operating_outflows_monthly": "900000"}, # cf margin 0.10 -> 120, dscr 1.30 -> 60
        "reconciliation_metrics": {"gst_bank_ratio": "0.92"}, # ratio 0.92 -> 120
        "working_capital_metrics": {"operating_cycle_days": "65"}, # cycle 65 -> 60
        "obligation_verification_state": "VERIFIED",
        "verified_existing_debt_service_monthly": "25000",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    # p1=120, p2=120, p3=120, p4=60, p5=120, p6=60
    # Total = 600
    # FHI = 600 / 9 = 66.67
    assert fhi_data["vyapar_credit_health_score"] == 600
    assert fhi_data["financial_health_index"] == Decimal("66.67")

    breakdown = fhi_data["fhi_breakdown"]
    assert breakdown["operating_resilience"]["score"] == 120.0
    assert breakdown["cash_flow_health"]["score"] == 120.0
    assert breakdown["margin_stability"]["score"] == 120.0
    assert breakdown["working_capital_velocity"]["score"] == 60.0
    assert breakdown["gst_compliance"]["score"] == 120.0
    assert breakdown["obligation_discipline"]["score"] == 60.0
