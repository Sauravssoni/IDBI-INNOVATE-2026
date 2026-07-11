from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.policy import DecisionPolicy
from app.domain.financial.engine import FinancialCapacityEngine
from app.core.scoring.scorer import ScoringEngine


def run_case_stress_lab(
    features: Dict[str, Any],
    scores: Dict[str, Any],
    requested_amount: Decimal,
    requested_product: str,
    revenue_drop_pct: float = 15.0,
    interest_rate_hike_bps: int = 200
) -> Dict[str, Any]:
    """
    Authoritative backend computation of single-factor and combined downside stress scenarios.
    Accepts both canonical evaluation requirements and interactive parameter queries.
    Every scenario executes an exact, deterministic recomputation via FinancialCapacityEngine.
    """
    base_policy = DecisionPolicy(features, scores, requested_amount, requested_product)
    base_decision = base_policy.evaluate()
    base_limit = base_decision.get("binding_limit", Decimal("0.00"))

    def get_effective_dscr(cap: Dict[str, Any]) -> Decimal:
        post_dscr = cap.get("post_loan_dscr")
        if post_dscr is not None and Decimal(str(post_dscr)) > Decimal("0.00"):
            return Decimal(str(post_dscr))
        return Decimal("0.00")

    # Base Financial Capacity
    base_cap = FinancialCapacityEngine.compute_capacity_from_features(features, requested_amount, requested_product)
    base_dscr = get_effective_dscr(base_cap)
    base_inflows = base_cap["observed_operating_inflows_monthly"]
    base_outflows = base_cap["observed_operating_outflows_monthly"]
    base_existing_ds = base_cap["verified_existing_debt_service_monthly"]
    obligation_state = base_cap["obligation_verification_state"]

    scenarios = []

    # Helper for status grading
    def get_status(dscr: Optional[Decimal], free_cash: Decimal = Decimal("0.00")) -> str:
        if dscr is None or dscr == Decimal("0.00"):
            return "NOT_ASSESSABLE"
        if dscr >= Decimal("1.15"):
            return "PASS"
        elif dscr >= Decimal("1.00"):
            return "MARGINAL"
        return "FAIL"

    def get_custom_status(dscr: Optional[Decimal], free_cash: Decimal = Decimal("0.00")) -> str:
        if dscr is None or dscr == Decimal("0.00"):
            return "NOT_ASSESSABLE"
        if dscr >= Decimal("1.25"):
            return "SECURE"
        elif dscr >= Decimal("1.05"):
            return "VULNERABLE"
        return "DISTRESSED"

    def recompute_scenario(scenario_features: Dict[str, Any], rate: Decimal = Decimal("0.135")) -> Dict[str, Any]:
        scenario_scores = ScoringEngine(scenario_features).compute_all_scores()
        scenario_cap = FinancialCapacityEngine.compute_capacity_from_features(
            scenario_features,
            requested_amount,
            requested_product,
            custom_annual_rate=rate,
        )
        scenario_policy = DecisionPolicy(scenario_features, scenario_scores, requested_amount, requested_product).evaluate()
        binding_details = scenario_policy.get("limit_details") or [scenario_cap.get("product_limits", {}).get(scenario_cap.get("requested_product_method"), {})]
        binding_constraint = None
        if binding_details and isinstance(binding_details[0], dict):
            binding_constraint = binding_details[0].get("binding_constraint")
        return {
            "scores": scenario_scores,
            "capacity": scenario_cap,
            "policy": scenario_policy,
            "fhi": scenario_scores.get("financial_health_index"),
            "credit_health_score": scenario_scores.get("vyapar_credit_health_score"),
            "assessment_range": scenario_scores.get("score_range"),
            "post_loan_dscr": scenario_cap.get("post_loan_dscr"),
            "supportable_amount": float(Decimal(str(scenario_policy.get("binding_limit", 0) or 0))),
            "decision": scenario_policy.get("decision"),
            "binding_constraint": binding_constraint,
            "breached_rules": scenario_policy.get("reasons", []),
        }

    def scenario_payload(
        scenario_id: str,
        name: str,
        description: str,
        scenario_features: Dict[str, Any],
        policy_rule_id: str,
        rate: Decimal = Decimal("0.135"),
    ) -> Dict[str, Any]:
        result = recompute_scenario(scenario_features, rate)
        dscr_dec = Decimal(str(result["post_loan_dscr"])) if result["post_loan_dscr"] is not None else Decimal("0.00")
        status = get_status(dscr_dec if dscr_dec > 0 else None)
        return {
            "scenario_id": scenario_id,
            "name": name,
            "description": description,
            "recomputed_dscr": float(dscr_dec),
            "recomputed_limit": result["supportable_amount"],
            "status": status,
            "policy_rule_id": policy_rule_id,
            "transition_explanation": f"{name}: policy state {base_decision.get('decision')} -> {result['decision']}.",
            "before": {
                "fhi": scores.get("financial_health_index"),
                "credit_health_score": scores.get("vyapar_credit_health_score"),
                "assessment_range": scores.get("score_range"),
                "post_loan_dscr": base_cap.get("post_loan_dscr"),
                "supportable_amount": float(base_limit),
                "decision": base_decision.get("decision"),
                "binding_constraint": None,
                "breached_rules": base_decision.get("reasons", []),
            },
            "after": {
                "fhi": result["fhi"],
                "credit_health_score": result["credit_health_score"],
                "assessment_range": result["assessment_range"],
                "post_loan_dscr": result["post_loan_dscr"],
                "supportable_amount": result["supportable_amount"],
                "decision": result["decision"],
                "binding_constraint": result["binding_constraint"],
                "breached_rules": result["breached_rules"],
            },
        }

    # 1. Revenue Drop -15%
    s1_features = features.copy()
    s1_inflows = (base_inflows * Decimal("0.85")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s1_bank = dict(features.get("bank_metrics", {}))
    s1_bank["operating_inflows_monthly"] = str(s1_inflows)
    s1_bank["avg_monthly_credits"] = str(s1_inflows)
    s1_features["bank_metrics"] = s1_bank
    if "monthly_revenue_inr" in s1_features:
        s1_features["monthly_revenue_inr"] = str(s1_inflows)
    
    scenarios.append(scenario_payload("REVENUE_DROP_15", "Revenue Drop (-15%)", "Simulates a 15% reduction in verified operating cash inflows.", s1_features, "POL-STR-001"))

    # 2. Interest Rate Hike +200bps (+2%) on proposed facility. Existing EMI remains fixed
    # unless exact facility terms are available for re-amortisation.
    s2_features = features.copy()
    s2_features["verified_existing_debt_service_monthly"] = str(base_existing_ds)
    s2_features["obligation_verification_state"] = obligation_state

    scenarios.append(scenario_payload(
        "RATE_HIKE_200BPS",
        "Interest Rate Hike (+200bps)",
        "Re-amortises proposed facility at shocked rate. Existing facility EMI is held constant because principal/rate/remaining-tenure fields are unavailable.",
        s2_features,
        "POL-STR-002",
        Decimal("0.155"),
    ))

    # 3. COGS / Outflows Increase +10%
    s3_features = features.copy()
    s3_outflows = (base_outflows * Decimal("1.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s3_bank = dict(features.get("bank_metrics", {}))
    s3_bank["operating_outflows_monthly"] = str(s3_outflows)
    s3_bank["avg_monthly_debits"] = str(s3_outflows)
    s3_features["bank_metrics"] = s3_bank

    scenarios.append(scenario_payload("COGS_INCREASE_10", "COGS / Outflow Increase (+10%)", "Simulates a 10% inflation in operating expenses and supplier debits.", s3_features, "POL-STR-003"))

    # 4. Combined Downside Shock (-15% revenue, +10% cogs, +200bps rate)
    s4_features = features.copy()
    s4_inflows = (base_inflows * Decimal("0.85")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s4_outflows = (base_outflows * Decimal("1.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s4_existing_ds = base_existing_ds

    s4_bank = dict(features.get("bank_metrics", {}))
    s4_bank["operating_inflows_monthly"] = str(s4_inflows)
    s4_bank["operating_outflows_monthly"] = str(s4_outflows)
    s4_bank["avg_monthly_credits"] = str(s4_inflows)
    s4_bank["avg_monthly_debits"] = str(s4_outflows)
    s4_features["bank_metrics"] = s4_bank
    s4_features["verified_existing_debt_service_monthly"] = str(s4_existing_ds)
    s4_features["obligation_verification_state"] = obligation_state

    scenarios.append(scenario_payload("COMBINED_DOWNSIDE", "Combined Downside Shock", "Simulates simultaneous -15% revenue contraction, +10% expense inflation, and +200bps proposed-rate shock.", s4_features, "POL-STR-004", Decimal("0.155")))

    overall_stress_status = (
        "NOT_ASSESSABLE" if any(s["status"] == "NOT_ASSESSABLE" for s in scenarios)
        else "PASS" if all(s["status"] == "PASS" for s in scenarios)
        else "FAIL" if any(s["status"] == "FAIL" for s in scenarios)
        else "MARGINAL"
    )

    # Interactive Custom Query Recomputation with Re-amortized Shocked Rate
    custom_rev_factor = Decimal("1") - (Decimal(str(revenue_drop_pct)) / Decimal("100"))
    custom_inflows = (base_inflows * custom_rev_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rate_hike_dec = (Decimal(str(interest_rate_hike_bps)) / Decimal("10000"))
    custom_ds = base_existing_ds
    custom_annual_rate_dec = Decimal("0.135") + rate_hike_dec

    custom_features = features.copy()
    custom_bank = dict(features.get("bank_metrics", {}))
    custom_bank["operating_inflows_monthly"] = str(custom_inflows)
    custom_features["bank_metrics"] = custom_bank
    custom_features["verified_existing_debt_service_monthly"] = str(custom_ds)
    custom_features["obligation_verification_state"] = obligation_state

    custom_cap = FinancialCapacityEngine.compute_capacity_from_features(
        custom_features,
        requested_amount,
        requested_product,
        custom_annual_rate=custom_annual_rate_dec
    )
    custom_dscr = get_effective_dscr(custom_cap)
    custom_limit = custom_cap.get("binding_product_limit", Decimal("0.00"))
    custom_status = get_custom_status(custom_dscr, custom_inflows - base_outflows)
    baseline_status = get_custom_status(base_dscr, base_inflows - base_outflows)

    return {
        "overall_stress_status": overall_stress_status,
        "base_dscr": float(base_dscr),
        "base_binding_limit": float(base_limit),
        "scenarios": scenarios,
        "authoritative_engine": "Vyapar Pulse Stress Lab Engine v2.0",
        "calculation_version": "2.0-STRESS-CANONICAL",
        "scenario": {
            "revenue_drop_pct": revenue_drop_pct,
            "interest_rate_hike_bps": interest_rate_hike_bps
        },
        "baseline": {
            "dscr": float(base_dscr),
            "max_loan_amount": float(base_limit),
            "status": baseline_status
        },
        "stressed": {
            "dscr": float(custom_dscr),
            "max_loan_amount": float(custom_limit),
            "status": custom_status
        },
        "summary": f"Stressed DSCR under {revenue_drop_pct}% revenue drop and +{interest_rate_hike_bps}bps rate hike is {custom_dscr:.2f} ({custom_status})."
    }
