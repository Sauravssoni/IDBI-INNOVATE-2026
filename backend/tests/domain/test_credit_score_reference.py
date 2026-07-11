from decimal import Decimal, ROUND_HALF_UP
import pytest
from app.core.scoring.scorer import ScoringEngine


def test_fhi_and_credit_score_perfect_verified_case():
    features = {
        "bank_metrics": {"dscr": "2.2", "operating_inflows_monthly": "1000000"},
        "reconciliation_metrics": {"gst_bank_ratio": "1.01"},
        "working_capital_metrics": {"operating_cycle_days": "40"},
        "obligation_verification_state": "VERIFIED",
        "verified_existing_debt_service_monthly": "0",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert fhi_data["financial_health_index"] == 100.0
    assert fhi_data["vyapar_credit_health_score"] == 900
    assert "proprietary institutional diagnostic indicators" in fhi_data["credit_health_disclaimer"]
    assert "not constitute an official credit bureau score" in fhi_data["credit_health_disclaimer"]

    breakdown = fhi_data["fhi_breakdown"]
    assert breakdown["cash_flow_strength"]["score"] == 35.0
    assert breakdown["cash_flow_strength"]["status"] == "VERIFIED"
    assert breakdown["gst_banking_variance"]["score"] == 25.0
    assert breakdown["working_capital_efficiency"]["score"] == 20.0
    assert breakdown["existing_debt_service_stress"]["score"] == 20.0

    # Verify canonical 6 pillars (20 + 25 + 15 + 20 + 10 + 10 = 100)
    assert breakdown["liquidity"]["score"] == 20.0
    assert breakdown["cash_flow_capacity"]["score"] == 25.0
    assert breakdown["revenue_growth"]["score"] == 15.0
    assert breakdown["repayment_burden"]["score"] == 20.0
    assert breakdown["compliance_governance"]["score"] == 10.0
    assert breakdown["concentration_risk"]["score"] == 10.0


def test_fhi_and_credit_score_missing_data_abstention():
    features = {
        "bank_metrics": {"dscr": "UNKNOWN"},
        "reconciliation_metrics": {},
        "working_capital_metrics": {"operating_cycle_days": "UNKNOWN"},
        "obligation_verification_state": "UNKNOWN_OBLIGATIONS",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    assert fhi_data["financial_health_index"] == 0.0
    assert fhi_data["vyapar_credit_health_score"] == 300

    breakdown = fhi_data["fhi_breakdown"]
    assert breakdown["cash_flow_strength"]["score"] == 0.0
    assert breakdown["cash_flow_strength"]["status"] == "MISSING_DATA"
    assert breakdown["gst_banking_variance"]["score"] == 0.0
    assert breakdown["gst_banking_variance"]["status"] == "MISSING_DATA"
    assert breakdown["working_capital_efficiency"]["score"] == 0.0
    assert breakdown["working_capital_efficiency"]["status"] == "MISSING_DATA"
    assert breakdown["existing_debt_service_stress"]["score"] == 0.0
    assert breakdown["existing_debt_service_stress"]["status"] == "MISSING_DATA"

    # Verify canonical 6 pillars abstention
    for pillar in ["liquidity", "cash_flow_capacity", "revenue_growth", "repayment_burden", "compliance_governance", "concentration_risk"]:
        assert breakdown[pillar]["score"] == 0.0
        assert breakdown[pillar]["status"] == "MISSING_DATA"


def test_fhi_and_credit_score_intermediate_values():
    features = {
        "bank_metrics": {"dscr": "1.30", "operating_inflows_monthly": "100000"},
        "reconciliation_metrics": {"gst_bank_ratio": "0.92"},
        "working_capital_metrics": {"operating_cycle_days": "65"},
        "obligation_verification_state": "VERIFIED",
        "verified_existing_debt_service_monthly": "25000",
    }
    engine = ScoringEngine(features)
    fhi_data = engine.compute_fhi_and_credit_score()

    # Canonical 6 pillars:
    # Liquidity (20%): DSCR 1.30 -> 12.0
    # Cash-flow capacity (25%): DSCR 1.30 -> 15.0
    # Revenue/growth (15%): verified bank + verified dscr -> 12.0
    # Repayment burden (20%): 25000/100000 = 0.25 -> 12.0
    # Compliance (10%): ratio 0.92 -> 8.0
    # Concentration (10%): cycle 65 -> 6.0
    # Total FHI = 12 + 15 + 12 + 12 + 8 + 6 = 65.0
    # Credit Score = 300 + 6 * 65 = 690
    assert fhi_data["financial_health_index"] == 65.0
    assert fhi_data["vyapar_credit_health_score"] == 690

    breakdown = fhi_data["fhi_breakdown"]
    assert breakdown["cash_flow_strength"]["score"] == 21.0
    assert breakdown["gst_banking_variance"]["score"] == 20.0
    assert breakdown["working_capital_efficiency"]["score"] == 12.0
    assert breakdown["existing_debt_service_stress"]["score"] == 12.0

    # Check canonical 6 pillars intermediate
    assert breakdown["liquidity"]["score"] == 12.0
    assert breakdown["cash_flow_capacity"]["score"] == 15.0
    assert breakdown["revenue_growth"]["score"] == 12.0
    assert breakdown["repayment_burden"]["score"] == 12.0
    assert breakdown["compliance_governance"]["score"] == 8.0
    assert breakdown["concentration_risk"]["score"] == 6.0
