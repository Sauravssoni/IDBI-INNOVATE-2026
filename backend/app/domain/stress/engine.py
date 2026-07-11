from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.policy import DecisionPolicy
from app.domain.financial.engine import FinancialCapacityEngine


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

    # Helper to obtain post-facility DSCR with fallback to current_dscr
    def get_effective_dscr(cap: Dict[str, Any]) -> Decimal:
        post_dscr = cap.get("post_loan_dscr")
        if post_dscr is not None and Decimal(str(post_dscr)) > Decimal("0.00"):
            return Decimal(str(post_dscr))
        curr_dscr = cap.get("current_dscr")
        if curr_dscr is not None and Decimal(str(curr_dscr)) > Decimal("0.00"):
            return Decimal(str(curr_dscr))
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
            return "PASS" if free_cash > Decimal("0.00") else "FAIL"
        if dscr >= Decimal("1.15"):
            return "PASS"
        elif dscr >= Decimal("1.00"):
            return "MARGINAL"
        return "FAIL"

    def get_custom_status(dscr: Optional[Decimal], free_cash: Decimal = Decimal("0.00")) -> str:
        if dscr is None or dscr == Decimal("0.00"):
            return "SECURE" if free_cash > Decimal("0.00") else "DISTRESSED"
        if dscr >= Decimal("1.25"):
            return "SECURE"
        elif dscr >= Decimal("1.05"):
            return "VULNERABLE"
        return "DISTRESSED"

    # 1. Revenue Drop -15%
    s1_features = features.copy()
    s1_inflows = (base_inflows * Decimal("0.85")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s1_bank = dict(features.get("bank_metrics", {}))
    s1_bank["operating_inflows_monthly"] = str(s1_inflows)
    s1_bank["avg_monthly_credits"] = str(s1_inflows)
    s1_features["bank_metrics"] = s1_bank
    if "monthly_revenue_inr" in s1_features:
        s1_features["monthly_revenue_inr"] = str(s1_inflows)
    
    s1_cap = FinancialCapacityEngine.compute_capacity_from_features(s1_features, requested_amount, requested_product)
    s1_dscr = get_effective_dscr(s1_cap)
    s1_limit = s1_cap.get("binding_product_limit", Decimal("0.00"))
    s1_status = get_status(s1_dscr, s1_inflows - base_outflows)

    scenarios.append({
        "scenario_id": "REVENUE_DROP_15",
        "name": "Revenue Drop (-15%)",
        "description": "Simulates a 15% reduction in verified operating cash inflows.",
        "recomputed_dscr": float(s1_dscr),
        "recomputed_limit": float(s1_limit),
        "status": s1_status,
        "policy_rule_id": "POL-STR-001",
        "transition_explanation": (
            f"Under a 15% revenue drop, DSCR transitions from {base_dscr:.2f} to {s1_dscr:.2f}. " +
            ("Supportable limit remains robust above requested requirement." if s1_status == "PASS" else
             f"DSCR breaches institutional thresholds, transitioning policy state towards {s1_status}.")
        )
    })

    # 2. Interest Rate Hike +200bps (+2%) on floating debt service and re-amortized facility
    s2_features = features.copy()
    s2_existing_ds = (base_existing_ds * Decimal("1.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s2_features["verified_existing_debt_service_monthly"] = str(s2_existing_ds)
    s2_features["obligation_verification_state"] = obligation_state

    s2_cap = FinancialCapacityEngine.compute_capacity_from_features(s2_features, requested_amount, requested_product, custom_annual_rate=Decimal("0.155"))
    s2_dscr = get_effective_dscr(s2_cap)
    s2_limit = s2_cap.get("binding_product_limit", Decimal("0.00"))
    s2_status = get_status(s2_dscr, base_inflows - base_outflows)

    scenarios.append({
        "scenario_id": "RATE_HIKE_200BPS",
        "name": "Interest Rate Hike (+200bps)",
        "description": "Simulates a +2.0% increase in borrowing costs across existing and proposed facilities.",
        "recomputed_dscr": float(s2_dscr),
        "recomputed_limit": float(s2_limit),
        "status": s2_status,
        "policy_rule_id": "POL-STR-002",
        "transition_explanation": (
            f"Under a +200bps rate shock, DSCR moves from {base_dscr:.2f} to {s2_dscr:.2f}. " +
            ("Interest rate shock is well absorbed within existing cash conversion headroom." if s2_status == "PASS" else
             f"Higher debt service reduces headroom below minimum institutional tolerance ({s2_status}).")
        )
    })

    # 3. COGS / Outflows Increase +10%
    s3_features = features.copy()
    s3_outflows = (base_outflows * Decimal("1.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s3_bank = dict(features.get("bank_metrics", {}))
    s3_bank["operating_outflows_monthly"] = str(s3_outflows)
    s3_bank["avg_monthly_debits"] = str(s3_outflows)
    s3_features["bank_metrics"] = s3_bank

    s3_cap = FinancialCapacityEngine.compute_capacity_from_features(s3_features, requested_amount, requested_product)
    s3_dscr = get_effective_dscr(s3_cap)
    s3_limit = s3_cap.get("binding_product_limit", Decimal("0.00"))
    s3_status = get_status(s3_dscr, base_inflows - s3_outflows)

    scenarios.append({
        "scenario_id": "COGS_INCREASE_10",
        "name": "COGS / Outflow Increase (+10%)",
        "description": "Simulates a 10% inflation in operating expenses and supplier debits.",
        "recomputed_dscr": float(s3_dscr),
        "recomputed_limit": float(s3_limit),
        "status": s3_status,
        "policy_rule_id": "POL-STR-003",
        "transition_explanation": (
            f"With 10% higher supplier outflows, operating margin compresses and DSCR shifts from {base_dscr:.2f} to {s3_dscr:.2f}. " +
            ("Buffer is sufficient to maintain debt service without covenant breach." if s3_status == "PASS" else
             "Margin compression requires structural credit mitigation or facility sizing reduction.")
        )
    })

    # 4. Combined Downside Shock (-15% revenue, +10% cogs, +200bps rate)
    s4_features = features.copy()
    s4_inflows = (base_inflows * Decimal("0.85")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s4_outflows = (base_outflows * Decimal("1.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s4_existing_ds = (base_existing_ds * Decimal("1.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    s4_bank = dict(features.get("bank_metrics", {}))
    s4_bank["operating_inflows_monthly"] = str(s4_inflows)
    s4_bank["operating_outflows_monthly"] = str(s4_outflows)
    s4_bank["avg_monthly_credits"] = str(s4_inflows)
    s4_bank["avg_monthly_debits"] = str(s4_outflows)
    s4_features["bank_metrics"] = s4_bank
    s4_features["verified_existing_debt_service_monthly"] = str(s4_existing_ds)
    s4_features["obligation_verification_state"] = obligation_state

    s4_cap = FinancialCapacityEngine.compute_capacity_from_features(s4_features, requested_amount, requested_product, custom_annual_rate=Decimal("0.155"))
    s4_dscr = get_effective_dscr(s4_cap)
    s4_limit = s4_cap.get("binding_product_limit", Decimal("0.00"))
    s4_status = get_status(s4_dscr, s4_inflows - s4_outflows)

    scenarios.append({
        "scenario_id": "COMBINED_DOWNSIDE",
        "name": "Combined Downside Shock",
        "description": "Simulates simultaneous -15% revenue contraction, +10% expense inflation, and +200bps rate shock.",
        "recomputed_dscr": float(s4_dscr),
        "recomputed_limit": float(s4_limit),
        "status": s4_status,
        "policy_rule_id": "POL-STR-004",
        "transition_explanation": (
            f"Under severe combined downside, DSCR degrades from {base_dscr:.2f} to {s4_dscr:.2f} and supportable limit adjusts to INR {float(s4_limit):,.2f}. " +
            ("Case maintains viability under severe macro-economic stress." if s4_status == "PASS" else
             f"Severe macroeconomic deterioration triggers explicit policy transition from {base_decision.get('decision')} to DECLINE or CONDITIONAL.")
        )
    })

    overall_stress_status = "PASS" if all(s["status"] == "PASS" for s in scenarios) else ("FAIL" if any(s["status"] == "FAIL" for s in scenarios) else "MARGINAL")

    # Interactive Custom Query Recomputation with Re-amortized Shocked Rate
    custom_rev_factor = Decimal("1") - (Decimal(str(revenue_drop_pct)) / Decimal("100"))
    custom_inflows = (base_inflows * custom_rev_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rate_hike_dec = (Decimal(str(interest_rate_hike_bps)) / Decimal("10000"))
    custom_rate_factor = Decimal("1") + rate_hike_dec * Decimal("0.75")
    custom_ds = (base_existing_ds * custom_rate_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
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
