from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.policy import DecisionPolicy
from app.core.decision.limits import SafeLimitEngine


def run_case_stress_lab(features: Dict[str, Any], scores: Dict[str, Any], requested_amount: Decimal, requested_product: str, revenue_drop_pct: float = 15.0, interest_rate_hike_bps: int = 200) -> Dict[str, Any]:
    """
    Authoritative backend computation of single-factor and combined downside stress scenarios.
    Accepts both canonical evaluation requirements and interactive parameter queries.
    """
    base_policy = DecisionPolicy(features, scores, requested_amount, requested_product)
    base_decision = base_policy.evaluate()
    base_limit = base_decision.get("binding_limit", Decimal("0"))
    
    # Base DSCR
    bank = features.get("bank_metrics", {})
    try:
        base_credits = Decimal(str(bank.get("avg_monthly_credits", features.get("banking_inflow_inr", features.get("monthly_revenue_inr", "0")))))
        base_debits = Decimal(str(bank.get("avg_monthly_debits", features.get("banking_outflow_inr", features.get("monthly_expenses_inr", "0")))))
        dscr_str = bank.get("dscr")
        if dscr_str and Decimal(str(dscr_str)) > 0:
            base_obligations = base_credits / Decimal(str(dscr_str))
        elif base_debits > 0:
            base_obligations = base_debits * Decimal("0.20")
        else:
            base_obligations = Decimal("0")
        base_dscr = base_credits / base_obligations if base_obligations > 0 else Decimal("0.00")
    except Exception:
        base_credits = Decimal("0")
        base_debits = Decimal("0")
        base_obligations = Decimal("0")
        base_dscr = Decimal("0.00")

    scenarios = []
    
    # 1. Revenue Drop -15%
    s1_features = features.copy()
    s1_credits = base_credits * Decimal("0.85")
    s1_bank = bank.copy() if isinstance(bank, dict) else {}
    s1_bank["avg_monthly_credits"] = str(s1_credits)
    s1_features["bank_metrics"] = s1_bank
    s1_features["monthly_revenue_inr"] = str(s1_credits)
    s1_dscr = (s1_credits / base_obligations) if base_obligations > 0 else Decimal("0.00")
    s1_limits = SafeLimitEngine.calculate_all_limits(s1_features)
    s1_limit = min((l["calculated_limit"] for l in s1_limits), default=Decimal("0")) if s1_limits else Decimal("0")
    
    s1_status = "PASS" if s1_dscr >= Decimal("1.15") else ("MARGINAL" if s1_dscr >= Decimal("1.00") else "FAIL")
    scenarios.append({
        "scenario_id": "REVENUE_DROP_15",
        "name": "Revenue Drop (-15%)",
        "description": "Simulates a 15% reduction in gross monthly cash inflows across account feeds.",
        "recomputed_dscr": float(s1_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "recomputed_limit": float(s1_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "status": s1_status,
        "policy_rule_id": "POL-STR-001",
        "transition_explanation": (
            f"Under a 15% revenue drop, DSCR transitions from {base_dscr:.2f} to {s1_dscr:.2f}. " +
            ("Supportable limit remains robust above requested requirement." if s1_status == "PASS" else
             f"DSCR breaches the 1.15 institutional threshold, transitioning policy state towards {s1_status}.")
        )
    })

    # 2. Interest Rate Hike +200bps (+2%)
    s2_obligations = base_obligations * Decimal("1.15")  # +15% debt service due to rate hike across floating facilities
    s2_dscr = (base_credits / s2_obligations) if s2_obligations > 0 else Decimal("0.00")
    s2_status = "PASS" if s2_dscr >= Decimal("1.15") else ("MARGINAL" if s2_dscr >= Decimal("1.00") else "FAIL")
    scenarios.append({
        "scenario_id": "RATE_HIKE_200BPS",
        "name": "Interest Rate Hike (+200bps)",
        "description": "Simulates a +2.0% increase in borrowing costs across existing and proposed debt facilities.",
        "recomputed_dscr": float(s2_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "recomputed_limit": float((base_limit * Decimal("0.90")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "status": s2_status,
        "policy_rule_id": "POL-STR-002",
        "transition_explanation": (
            f"Under a +200bps rate shock, DSCR moves from {base_dscr:.2f} to {s2_dscr:.2f}. " +
            ("Interest rate shock is well absorbed within existing cash conversion headroom." if s2_status == "PASS" else
             f"Higher debt service reduces headroom below minimum institutional tolerance ({s2_status}).")
        )
    })

    # 3. COGS / Outflows Increase +10%
    s3_debits = base_debits * Decimal("1.10")
    s3_fcf = max(Decimal("0"), base_credits - s3_debits)
    s3_dscr = (base_credits / (base_obligations + (base_debits * Decimal("0.10")))) if (base_obligations + (base_debits * Decimal("0.10"))) > 0 else Decimal("0.00")
    s3_status = "PASS" if s3_dscr >= Decimal("1.15") else ("MARGINAL" if s3_dscr >= Decimal("1.00") else "FAIL")
    scenarios.append({
        "scenario_id": "COGS_INCREASE_10",
        "name": "COGS / Outflow Increase (+10%)",
        "description": "Simulates a 10% inflation in operating expenses and supplier payment debits.",
        "recomputed_dscr": float(s3_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "recomputed_limit": float((base_limit * Decimal("0.88")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "status": s3_status,
        "policy_rule_id": "POL-STR-003",
        "transition_explanation": (
            f"With 10% higher supplier outflows, operating margin compresses and DSCR shifts from {base_dscr:.2f} to {s3_dscr:.2f}. " +
            ("Buffer is sufficient to maintain debt service without covenant breach." if s3_status == "PASS" else
             "Margin compression requires structural credit mitigation or facility sizing reduction.")
        )
    })

    # 4. Combined Downside Shock (-15% revenue and +200bps interest)
    s4_credits = base_credits * Decimal("0.85")
    s4_obligations = base_obligations * Decimal("1.15")
    s4_dscr = (s4_credits / s4_obligations) if s4_obligations > 0 else Decimal("0.00")
    s4_limit = float((base_limit * Decimal("0.70")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    s4_status = "PASS" if s4_dscr >= Decimal("1.15") else ("MARGINAL" if s4_dscr >= Decimal("1.00") else "FAIL")
    scenarios.append({
        "scenario_id": "COMBINED_DOWNSIDE",
        "name": "Combined Downside Shock",
        "description": "Simulates simultaneous -15% revenue contraction and +200bps interest rate shock.",
        "recomputed_dscr": float(s4_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "recomputed_limit": s4_limit,
        "status": s4_status,
        "policy_rule_id": "POL-STR-004",
        "transition_explanation": (
            f"Under severe combined downside, DSCR degrades from {base_dscr:.2f} to {s4_dscr:.2f} and max supportable limit contracts to INR {s4_limit:,.2f}. " +
            ("Case maintains viability under severe macro-economic stress." if s4_status == "PASS" else
             f"Severe macroeconomic deterioration triggers explicit policy transition from {base_decision.get('decision')} to DECLINE under stress.")
        )
    })

    overall_stress_status = "PASS" if all(s["status"] == "PASS" for s in scenarios) else ("FAIL" if any(s["status"] == "FAIL" for s in scenarios) else "MARGINAL")

    # Compute custom parameter scenario for interactive / direct queries
    custom_rev_factor = Decimal("1") - (Decimal(str(revenue_drop_pct)) / Decimal("100"))
    custom_credits = base_credits * custom_rev_factor
    custom_rate_factor = Decimal("1") + (Decimal(str(interest_rate_hike_bps)) / Decimal("10000")) * Decimal("0.75")
    custom_obligations = base_obligations * custom_rate_factor if base_obligations > 0 else (base_debits * Decimal("0.20") * custom_rate_factor)
    custom_dscr = (custom_credits / custom_obligations) if custom_obligations > 0 else Decimal("0.00")
    
    # Calculate custom stressed limit based on proportional revenue drop and rate hike impact
    limit_reduction_factor = custom_rev_factor * (Decimal("1") - (Decimal(str(interest_rate_hike_bps)) / Decimal("20000")))
    custom_stressed_limit = base_limit * max(Decimal("0.10"), limit_reduction_factor)
    custom_status = "SECURE" if custom_dscr >= Decimal("1.25") else ("VULNERABLE" if custom_dscr >= Decimal("1.05") else "DISTRESSED")

    return {
        "overall_stress_status": overall_stress_status,
        "base_dscr": float(base_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "base_binding_limit": float(base_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "scenarios": scenarios,
        "authoritative_engine": "Vyapar Pulse Stress Lab Engine v2.0",
        "calculation_version": "2.0-STRESS-CANONICAL",
        "scenario": {
            "revenue_drop_pct": revenue_drop_pct,
            "interest_rate_hike_bps": interest_rate_hike_bps
        },
        "baseline": {
            "dscr": float(base_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "max_loan_amount": float(base_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "status": "SECURE" if base_dscr >= Decimal("1.25") else ("VULNERABLE" if base_dscr >= Decimal("1.05") else "DISTRESSED")
        },
        "stressed": {
            "dscr": float(custom_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "max_loan_amount": float(custom_stressed_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "status": custom_status
        },
        "summary": f"Stressed DSCR under {revenue_drop_pct}% revenue drop and +{interest_rate_hike_bps}bps rate hike is {custom_dscr:.2f} ({custom_status})."
    }
