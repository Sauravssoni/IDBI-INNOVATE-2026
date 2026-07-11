from decimal import Decimal
from hypothesis import given, strategies as st
from app.core.decision.policy import DecisionPolicy
from app.db.orm.cases import SystemRecommendation
from app.db.orm.org import ProductType


@given(
    revenue=st.decimals(
        min_value=Decimal("100000.00"), max_value=Decimal("100000000.00"), places=2
    ),
    expenses=st.decimals(
        min_value=Decimal("50000.00"), max_value=Decimal("50000000.00"), places=2
    ),
    requested_amount=st.decimals(
        min_value=Decimal("10000.00"), max_value=Decimal("5000000.00"), places=2
    ),
    evidence_score=st.floats(min_value=50.0, max_value=100.0),
)
def test_monotonicity_higher_revenue_yields_higher_or_equal_limit(
    revenue: Decimal,
    expenses: Decimal,
    requested_amount: Decimal,
    evidence_score: float,
):
    """
    Test that increasing revenue (while holding other factors constant)
    never decreases the calculated binding limit.
    """
    features_base = {
        "consent_status": "VALID",
        "integrity_flag": False,
        "monthly_revenue_inr": str(revenue),
        "monthly_expenses_inr": str(expenses),
        "banking_inflow_inr": str(revenue),
        "banking_outflow_inr": str(expenses),
        "average_bank_balance": "500000.00",
    }

    scores = {
        "evidence_confidence_score": evidence_score,
        "financial_health_score": 80.0,
    }

    policy_base = DecisionPolicy(
        features_base, scores, requested_amount, ProductType.WORKING_CAPITAL_LINE
    )
    decision_base = policy_base.evaluate()
    limit_base = decision_base["binding_limit"]

    # Increase revenue
    features_increased = features_base.copy()
    features_increased["monthly_revenue_inr"] = str(revenue * Decimal("1.5"))
    features_increased["banking_inflow_inr"] = str(revenue * Decimal("1.5"))

    policy_increased = DecisionPolicy(
        features_increased, scores, requested_amount, ProductType.WORKING_CAPITAL_LINE
    )
    decision_increased = policy_increased.evaluate()
    limit_increased = decision_increased["binding_limit"]

    # Monotonicity property: Higher or equal revenue should yield higher or equal limit
    assert limit_increased >= limit_base


@given(
    requested_amount=st.decimals(
        min_value=Decimal("10000.00"), max_value=Decimal("5000000.00"), places=2
    )
)
def test_decision_bounds_offers_never_exceed_binding_limit(requested_amount: Decimal):
    """
    Test that the generated offers (amount) never exceed the binding_limit.
    """
    features = {
        "consent_status": "VALID",
        "integrity_flag": False,
        "monthly_revenue_inr": "5000000.00",
        "monthly_expenses_inr": "3000000.00",
        "banking_inflow_inr": "5000000.00",
        "banking_outflow_inr": "3000000.00",
        "average_bank_balance": "1000000.00",
    }
    scores = {"evidence_confidence_score": 85.0, "financial_health_score": 90.0}

    policy = DecisionPolicy(
        features, scores, requested_amount, ProductType.WORKING_CAPITAL_LINE
    )
    decision = policy.evaluate()

    binding_limit = decision["binding_limit"]

    for offer in decision["offers"]:
        offer_amount = Decimal(offer["amount"])
        assert offer_amount <= binding_limit


@given(
    requested_amount=st.decimals(
        min_value=Decimal("10000000.00"), max_value=Decimal("50000000.00"), places=2
    )
)
def test_conditional_offer_when_requested_exceeds_limit(requested_amount: Decimal):
    """
    Test that if requested amount > binding limit, the decision is CONDITIONAL_OFFER.
    """
    # Fix features to ensure a limit less than 10,000,000
    features = {
        "consent_status": "VALID",
        "integrity_flag": False,
        "monthly_revenue_inr": "1000000.00",
        "monthly_expenses_inr": "800000.00",
        "banking_inflow_inr": "1000000.00",
        "banking_outflow_inr": "800000.00",
        "average_bank_balance": "50000.00",
    }
    scores = {"evidence_confidence_score": 80.0, "financial_health_score": 70.0}

    policy = DecisionPolicy(
        features, scores, requested_amount, ProductType.WORKING_CAPITAL_LINE
    )
    decision = policy.evaluate()

    binding_limit = decision["binding_limit"]

    if binding_limit > 0:
        assert binding_limit < requested_amount
        assert decision["decision"] == SystemRecommendation.CONDITIONAL_OFFER.value


def test_scoring_engine_returns_replayable_score_metadata():
    from app.core.scoring.scorer import ScoringEngine

    engine = ScoringEngine(
        {
            "gst_metrics": {"months_filed": 12},
            "reconciliation_metrics": {"gst_bank_ratio": 1.0},
        }
    )
    scores = engine.compute_all_scores()
    assert set(scores.keys()) == {
        "financial_health_score",
        "evidence_confidence_score",
        "resilience_score",
        "financial_health_index",
        "fhi_breakdown",
        "vyapar_credit_health_score",
        "credit_health_disclaimer",
        "credit_score_disclaimer",
        "assessment_certainty",
        "score_range",
        "missing_material_evidence",
        "scoring_version",
    }
    assert "band" not in scores
    assert scores["scoring_version"] == "3.0-EVIDENCE-CONDITIONED-FHI"


def test_generate_offers_no_percentage_fallbacks():
    features = {
        "consent_status": "VALID",
        "integrity_flag": False,
        "monthly_revenue_inr": "5000000.00",
        "monthly_expenses_inr": "3000000.00",
        "verified_existing_debt_service_monthly": "100000.00",
        "obligation_verification_state": "VERIFIED_OBLIGATIONS",
        "bank_metrics": {
            "operating_inflows_monthly": "5000000.00",
            "operating_outflows_monthly": "3000000.00",
        },
        "cibil_pulled": True,
        "average_bank_balance": "1000000.00",
        "gst_metrics": {"months_filed": 12, "avg_monthly_revenue": "5000000.00"},
        "reconciliation_metrics": {"gst_bank_ratio": 1.0},
        "eligible_receivables": 0,  # 0 receivables means RECEIVABLES_FINANCE should get 0 limit, NOT 100% of max borrowing
    }
    scores = {"evidence_confidence_score": 85.0, "financial_health_score": 90.0}

    policy = DecisionPolicy(
        features, scores, Decimal("2000000.00"), ProductType.WORKING_CAPITAL_LINE
    )
    decision = policy.evaluate()
    offers = decision["offers"]
    assert len(offers) == 3

    # Check each offer uses calculated product limits rather than arbitrary 60%/80%/100% fallbacks
    # RECEIVABLES_FINANCE offer (GROWTH tier / INVOICE_DISCOUNTING) must be 0.00 since eligible_receivables is 0
    rf_offer = next(o for o in offers if o["product_type"] == "INVOICE_DISCOUNTING")
    assert Decimal(rf_offer["amount"]) == Decimal("0.00")

    for offer in offers:
        amt = Decimal(offer["amount"])
        assert amt >= Decimal("0.00")
        assert amt <= decision["binding_limit"]
