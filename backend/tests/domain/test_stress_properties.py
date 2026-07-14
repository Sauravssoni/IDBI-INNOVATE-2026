from hypothesis import given, strategies as st, settings
from app.domain.financial.engine import FinancialCapacityEngine


@settings(max_examples=50)
@given(
    rev_drop=st.floats(min_value=0.0, max_value=0.9),
    expense_inc=st.floats(min_value=0.0, max_value=0.5),
    rate_hike=st.floats(min_value=0.0, max_value=0.1),
    tenor=st.integers(min_value=12, max_value=60),
)
def test_monotonicity_properties(rev_drop, expense_inc, rate_hike, tenor):
    base_features = {
        "gst_metrics": {"avg_monthly_revenue": 5000000.0},
        "bank_metrics": {
            "operating_inflows_monthly": 5000000.0,
            "operating_outflows_monthly": 4000000.0,
            "existing_monthly_emi": 100000.0,
            "avg_monthly_credits": 5000000.0,
            "avg_monthly_debits": 4000000.0,
        },
        "financials": {"ebitda_reported": 10000000.0},
        "requested_amount": 10000000.0,
        "requested_tenor_months": tenor,
    }

    # Calculate baseline
    base_result = FinancialCapacityEngine.compute_capacity_from_features(
        base_features, "TERM_LOAN", 10000000.0, 13.5, tenor
    )

    # Apply stress
    stressed_features = {
        "gst_metrics": {
            "avg_monthly_revenue": base_features["gst_metrics"]["avg_monthly_revenue"]
            * (1 - rev_drop)
        },
        "bank_metrics": {
            "operating_inflows_monthly": base_features["bank_metrics"][
                "operating_inflows_monthly"
            ]
            * (1 - rev_drop),
            "operating_outflows_monthly": base_features["bank_metrics"][
                "operating_outflows_monthly"
            ]
            * (1 + expense_inc),
            "existing_monthly_emi": base_features["bank_metrics"][
                "existing_monthly_emi"
            ],
            "avg_monthly_credits": base_features["bank_metrics"]["avg_monthly_credits"]
            * (1 - rev_drop),
            "avg_monthly_debits": base_features["bank_metrics"]["avg_monthly_debits"]
            * (1 + expense_inc),
        },
        "financials": {
            "ebitda_reported": base_features["financials"]["ebitda_reported"]
            * (1 - rev_drop)
        },
        "requested_amount": base_features["requested_amount"],
        "requested_tenor_months": tenor,
    }

    stressed_result = FinancialCapacityEngine.compute_capacity_from_features(
        stressed_features, "TERM_LOAN", 10000000.0, 13.5 + rate_hike, tenor
    )

    # The invariant: limit cannot increase under purely adverse conditions (lower revenue, higher expense, higher rate)
    assert stressed_result["max_borrowing_limit"] <= base_result["max_borrowing_limit"]

def test_canned_scenario_invariant_violation():
    from app.domain.stress.engine import run_case_stress_lab
    
    # We create a scenario where the stressed features magically result in a HIGHER limit than baseline,
    # which violates the monotonicity invariant. The engine should catch this and return INVARIANT_VIOLATION.
    # To simulate this easily, we can mock or construct features such that the base limit is extremely low,
    # but the recomputed limit is higher (e.g. by passing higher revenue in the "stressed" features if we could).
    # Since run_case_stress_lab hardcodes the stress multipliers, we can achieve this by passing a negative rate or manipulating base_limit directly if we mock.
    # The simplest way is to test the internal scenario_payload logic by injecting a scenario that breaks it.
    
    # But since scenario_payload is nested inside run_case_stress_lab, we must use run_case_stress_lab.
    # We can pass an artificially low base_limit to run_case_stress_lab.
    
    base_features = {
        "gst_metrics": {"avg_monthly_revenue": 5000000.0},
        "bank_metrics": {
            "operating_inflows_monthly": 5000000.0,
            "operating_outflows_monthly": 4000000.0,
            "existing_monthly_emi": 100000.0,
            "avg_monthly_credits": 5000000.0,
            "avg_monthly_debits": 4000000.0,
        },
        "financials": {"ebitda_reported": 10000000.0},
        "requested_amount": 1000000.0,
        "requested_tenor_months": 24,
    }
    
    from decimal import Decimal
    from unittest import mock
    
    # We mock DecisionPolicy.evaluate to return a very small base_limit.
    # The actual FinancialCapacityEngine (which is NOT mocked) will recompute
    # the capacity for the canned scenarios and yield a limit around 15 Million.
    # Since 15 Million > 100, the invariant check in scenario_payload will trip
    # and mark every scenario as INVARIANT_VIOLATION.
    def mock_eval_side_effect(*args, **kwargs):
        # We can use a counter attached to the function to track calls
        if not hasattr(mock_eval_side_effect, "calls"):
            mock_eval_side_effect.calls = 0
        
        mock_eval_side_effect.calls += 1
        if mock_eval_side_effect.calls == 1:
            return {"decision": "APPROVED", "binding_limit": Decimal("100.00"), "reasons": []}
        else:
            return {"decision": "APPROVED", "binding_limit": Decimal("50000.00"), "reasons": []}
            
    with mock.patch("app.domain.stress.engine.DecisionPolicy.evaluate") as mock_eval:
        mock_eval.side_effect = mock_eval_side_effect   
        result = run_case_stress_lab(
            features=base_features,
            scores={"evidence_confidence_score": 100, "financial_health_index": 850, "vyapar_credit_health_score": 850, "score_range": "EXCELLENT"},
            requested_amount=Decimal("1000000.00"),
            requested_product="TERM_LOAN",
        )
    
    scenarios = result["scenarios"]
    # All scenarios will compute a raw limit > 100.00 and fail the invariant.
    for s in scenarios:
        if s["scenario_id"] == "REVERSE_STRESS":
            continue
        assert s["status"] == "INVARIANT_VIOLATION"
        assert s["after"]["decision"] == "REJECTED"
        assert s["after"]["binding_constraint"] == "STRESS_MONOTONICITY_VIOLATION"
        assert s["offer_generated"] is False
