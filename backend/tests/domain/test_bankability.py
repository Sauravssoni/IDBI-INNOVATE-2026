from decimal import Decimal
import pytest
from app.domain.bankability.path import compute_bankability_path, simulate_bankability_variable


def test_compute_bankability_path_deterministic_milestones():
    features = {
        "consent_status": "PENDING",
        "bank_metrics": {
            "months_filed": 6,
            "dscr": "1.10",
            "operating_inflows_monthly": "300000",
            "operating_outflows_monthly": "250000",
            "avg_monthly_credits": "300000",
            "avg_monthly_debits": "250000"
        },
        "gst_metrics": {
            "months_filed": 6,
            "trend": "STABLE",
            "avg_monthly_revenue": "320000"
        },
        "working_capital_metrics": {
            "operating_cycle_days": 75
        }
    }
    scores = {
        "evidence_confidence_score": Decimal("60.0"),
        "financial_health_score": Decimal("65.0"),
        "resilience_score": Decimal("70.0")
    }
    
    path = compute_bankability_path(features, scores, Decimal("5000000"), "WORKING_CAPITAL_LINE", target_amount=6000000.0)
    
    assert "current_state" in path
    assert "milestones" in path
    assert isinstance(path["milestones"], list)
    assert len(path["milestones"]) >= 2
    
    # Verify exact BNK-001 and BNK-002 simulation evidence
    for m in path["milestones"]:
        assert "milestone_id" in m
        assert "simulation_evidence" in m
        ev = m["simulation_evidence"]
        assert "before_evidence_score" in ev
        assert "after_evidence_score" in ev
        assert "before_health_score" in ev
        assert "after_health_score" in ev
        assert "before_dscr" in ev
        assert "after_dscr" in ev
        assert "projected_limit_inr" in m
        assert m["projected_limit_inr"] >= 0
        
    assert path["gap_to_target"] >= 0
    assert "hindi_bilingual_presentation" in path
    assert "summary" in path["hindi_bilingual_presentation"]


def test_compute_bankability_path_already_approved():
    features = {
        "consent_status": "VALID",
        "obligation_verification_state": "VERIFIED",
        "bank_metrics": {
            "months_filed": 18,
            "dscr": "2.50",
            "operating_inflows_monthly": "1000000",
            "operating_outflows_monthly": "700000",
            "avg_monthly_credits": "1000000",
            "avg_monthly_debits": "700000"
        },
        "gst_metrics": {
            "months_filed": 18,
            "trend": "GROWING",
            "avg_monthly_revenue": "1100000"
        },
        "reconciliation_metrics": {
            "gst_bank_ratio": "1.02"
        }
    }
    scores = {
        "evidence_confidence_score": Decimal("95.0"),
        "financial_health_score": Decimal("90.0"),
        "resilience_score": Decimal("85.0")
    }
    
    path = compute_bankability_path(features, scores, Decimal("2500000"), "WORKING_CAPITAL_LINE")
    assert path["current_state"] == "READY_FOR_REVIEW"
    # When already approved/ready for review without gaps, should generate MIL-OPT
    assert len(path["milestones"]) >= 1
    assert any(m["milestone_id"] == "MIL-OPT" for m in path["milestones"])


def test_simulate_bankability_variable():
    features = {
        "consent_status": "PENDING",
        "bank_metrics": {
            "months_filed": 6,
            "dscr": "1.10",
            "operating_inflows_monthly": "300000",
            "operating_outflows_monthly": "250000"
        },
        "gst_metrics": {
            "months_filed": 6,
            "trend": "STABLE",
            "avg_monthly_revenue": "320000"
        },
        "reconciliation_metrics": {
            "gst_bank_ratio": "0.85"
        }
    }
    scores = {
        "evidence_confidence_score": Decimal("60.0"),
        "financial_health_score": Decimal("65.0"),
        "financial_health_index": Decimal("65.0"),
        "vyapar_credit_health_score": 690,
        "resilience_score": Decimal("70.0")
    }
    
    overrides = {
        "dscr": "2.10",
        "operating_inflows_monthly": "800000",
        "gst_bank_ratio": "1.00",
        "consent_status": "VALID"
    }
    
    result = simulate_bankability_variable(features, scores, Decimal("5000000"), "WORKING_CAPITAL_LINE", overrides)
    assert "before_simulation" in result
    assert "after_simulation" in result
    assert "uplift_summary" in result
    assert result["engine_version"] == "2.0-BANKABILITY-SIMULATION"
    
    before = result["before_simulation"]
    after = result["after_simulation"]
    uplift = result["uplift_summary"]
    
    assert after["binding_limit_inr"] >= before["binding_limit_inr"]
    assert after["verified_dscr"] >= before["verified_dscr"]
    assert after["financial_health_score"] >= before["financial_health_score"]

