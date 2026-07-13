import pytest
from decimal import Decimal
from app.core.scoring.scorer import ScoringEngine

def test_score_ledger_reconciliation():
    features = {
        "monthly_revenue_inr": 500000,
        "consent_status": "VALID",
        "obligation_verification_state": "VERIFIED_OBLIGATIONS",
        "bank_metrics": {
            "operating_inflows_monthly": 600000,
            "operating_outflows_monthly": 400000,
            "dscr": 1.5,
            "verified_debt_service_monthly": 50000,
            "transaction_categorization_summary": {
                "has_material_unresolved_activity": False
            }
        },
        "reconciliation_metrics": {
            "gst_bank_ratio": 1.02
        },
        "receivable_metrics": {
            "top_buyer_concentration": 0.15,
            "avg_payment_delay_days": 15
        },
        "operating_cycle_days": 30,
        "gst_metrics": {
            "months_filed": 12,
            "revenue_cv": 0.05,
            "trend": "GROWING",
            "gst_evidence_ids": ["EVD-GST-123"]
        },
        "verified_existing_debt_service_monthly": 50000,
        "current_dscr": 1.5,
        "post_loan_dscr": 1.3,
        "authoritative_evidence_ids": ["EVD-BANK-1", "EVD-BANK-2"]
    }

    engine = ScoringEngine(features)
    result = engine.compute_all_scores()
    
    assert "score_contribution_ledger" in result
    ledger = result["score_contribution_ledger"]
    
    assert len(ledger) > 1
    assert ledger[0]["pillar"] == "Base Score"
    assert ledger[0]["raw_points"] == 300.0
    
    # Check that final running score matches vyapar_credit_health_score
    final_running = ledger[-1]["running_score"]
    assert final_running == result["vyapar_credit_health_score"]

    # Monotonicity test: if we reduce debt service, the score should monotonically go up or stay the same
    features_less_debt = dict(features)
    features_less_debt["bank_metrics"] = dict(features["bank_metrics"])
    features_less_debt["bank_metrics"]["verified_debt_service_monthly"] = 10000
    features_less_debt["verified_existing_debt_service_monthly"] = 10000
    
    engine2 = ScoringEngine(features_less_debt)
    res2 = engine2.compute_all_scores()
    assert res2["vyapar_credit_health_score"] >= result["vyapar_credit_health_score"]

    # Check evidence lineage is not using static MISSING_BANK_EVD
    for entry in ledger:
        for ev in entry["evidence_ids"]:
            assert "MISSING" not in ev
            assert ev in ["EVD-GST-123", "EVD-BANK-1", "EVD-BANK-2"]
