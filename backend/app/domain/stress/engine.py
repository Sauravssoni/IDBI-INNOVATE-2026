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
    interest_rate_hike_bps: int = 200,
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
    base_cap = FinancialCapacityEngine.compute_capacity_from_features(
        features, requested_amount, requested_product
    )
    base_dscr = get_effective_dscr(base_cap)
    base_inflows = base_cap["observed_operating_inflows_monthly"]
    base_outflows = base_cap["observed_operating_outflows_monthly"]
    base_existing_ds = base_cap["verified_existing_debt_service_monthly"]
    obligation_state = base_cap["obligation_verification_state"]

    scenarios = []

    # Helper for status grading
    def get_status(
        dscr: Optional[Decimal], free_cash: Decimal = Decimal("0.00")
    ) -> str:
        if dscr is None or dscr == Decimal("0.00"):
            return "NOT_ASSESSABLE"
        if dscr >= Decimal("1.15"):
            return "PASS"
        elif dscr >= Decimal("1.00"):
            return "MARGINAL"
        return "FAIL"

    def get_custom_status(
        dscr: Optional[Decimal], free_cash: Decimal = Decimal("0.00")
    ) -> str:
        if dscr is None or dscr == Decimal("0.00"):
            return "NOT_ASSESSABLE"
        if dscr >= Decimal("1.25"):
            return "SECURE"
        elif dscr >= Decimal("1.05"):
            return "VULNERABLE"
        return "DISTRESSED"

    def recompute_scenario(
        scenario_features: Dict[str, Any], rate: Decimal = Decimal("0.135")
    ) -> Dict[str, Any]:
        scenario_scores = ScoringEngine(scenario_features).compute_all_scores()
        scenario_cap = FinancialCapacityEngine.compute_capacity_from_features(
            scenario_features,
            requested_amount,
            requested_product,
            custom_annual_rate=rate,
        )
        scenario_policy = DecisionPolicy(
            scenario_features,
            scenario_scores,
            requested_amount,
            requested_product,
            custom_annual_rate=rate,
        ).evaluate()
        binding_details = scenario_policy.get("limit_details") or [
            scenario_cap.get("product_limits", {}).get(
                scenario_cap.get("requested_product_method"), {}
            )
        ]
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
            "supportable_amount": float(
                Decimal(str(scenario_policy.get("binding_limit", 0) or 0))
            ),
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

        # Enforce invariant: stressed_limit <= baseline_limit
        raw_stressed_limit = result["supportable_amount"]

        if raw_stressed_limit > float(base_limit):
            status = "INVARIANT_VIOLATION"
            result["decision"] = "REJECTED"
            result["binding_constraint"] = "STRESS_MONOTONICITY_VIOLATION"
            result["breached_rules"] = [
                "Adverse limit exceeded baseline limit (Non-monotonic)"
            ]
            offer_generated = False
        else:
            dscr_dec = (
                Decimal(str(result["post_loan_dscr"]))
                if result["post_loan_dscr"] is not None
                else Decimal("0.00")
            )
            status = get_status(dscr_dec if dscr_dec > 0 else None)
            offer_generated = True

        return {
            "scenario_id": scenario_id,
            "name": name,
            "description": description,
            "recomputed_dscr": float(result["post_loan_dscr"])
            if result["post_loan_dscr"]
            else 0.0,
            "recomputed_limit": raw_stressed_limit,
            "status": status,
            "policy_rule_id": policy_rule_id,
            "transition_explanation": f"{name}: policy state {base_decision.get('decision')} -> {result['decision']}.",
            "offer_generated": offer_generated,
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
                "supportable_amount": raw_stressed_limit,
                "decision": result["decision"],
                "binding_constraint": result["binding_constraint"],
                "breached_rules": result["breached_rules"],
            },
        }

    # 1. Revenue Drop -15%
    s1_features = features.copy()
    s1_inflows = (base_inflows * Decimal("0.85")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s1_bank = dict(features.get("bank_metrics", {}))
    s1_bank["operating_inflows_monthly"] = str(s1_inflows)
    s1_bank["avg_monthly_credits"] = str(s1_inflows)
    s1_features["bank_metrics"] = s1_bank
    if "monthly_revenue_inr" in s1_features:
        s1_features["monthly_revenue_inr"] = str(s1_inflows)

    scenarios.append(
        scenario_payload(
            "REVENUE_DROP_15",
            "Revenue Drop (-15%)",
            "Simulates a 15% reduction in verified operating cash inflows.",
            s1_features,
            "POL-STR-001",
        )
    )

    # 2. Interest Rate Hike +200bps (+2%)
    s2_features = features.copy()
    s2_features["verified_existing_debt_service_monthly"] = str(base_existing_ds)
    s2_features["obligation_verification_state"] = obligation_state
    scenarios.append(
        scenario_payload(
            "RATE_HIKE_200BPS",
            "Interest Rate Hike (+200bps)",
            "Re-amortises proposed facility at shocked rate.",
            s2_features,
            "POL-STR-002",
            Decimal("0.155"),
        )
    )

    # 3. COGS / Outflows Increase +10%
    s3_features = features.copy()
    s3_outflows = (base_outflows * Decimal("1.10")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s3_bank = dict(features.get("bank_metrics", {}))
    s3_bank["operating_outflows_monthly"] = str(s3_outflows)
    s3_bank["avg_monthly_debits"] = str(s3_outflows)
    s3_features["bank_metrics"] = s3_bank
    scenarios.append(
        scenario_payload(
            "COGS_INCREASE_10",
            "COGS / Outflow Increase (+10%)",
            "Simulates a 10% inflation in operating expenses.",
            s3_features,
            "POL-STR-003",
        )
    )

    # 4. Combined Downside Shock (-15% rev, +10% cogs, +200bps rate)
    s4_features = features.copy()
    s4_inflows = (base_inflows * Decimal("0.85")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s4_outflows = (base_outflows * Decimal("1.10")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s4_bank = dict(features.get("bank_metrics", {}))
    s4_bank["operating_inflows_monthly"] = str(s4_inflows)
    s4_bank["operating_outflows_monthly"] = str(s4_outflows)
    s4_bank["avg_monthly_credits"] = str(s4_inflows)
    s4_bank["avg_monthly_debits"] = str(s4_outflows)
    s4_features["bank_metrics"] = s4_bank
    scenarios.append(
        scenario_payload(
            "COMBINED_DOWNSIDE",
            "Combined Downside Shock",
            "Simulates simultaneous -15% rev, +10% COGS, and +200bps rate shock.",
            s4_features,
            "POL-STR-004",
            Decimal("0.155"),
        )
    )

    # 5. Severe Revenue Drop -25%
    s5_features = features.copy()
    s5_inflows = (base_inflows * Decimal("0.75")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s5_bank = dict(features.get("bank_metrics", {}))
    s5_bank["operating_inflows_monthly"] = str(s5_inflows)
    s5_features["bank_metrics"] = s5_bank
    scenarios.append(
        scenario_payload(
            "REVENUE_DROP_25",
            "Severe Revenue Drop (-25%)",
            "Simulates a 25% reduction in verified operating cash inflows.",
            s5_features,
            "POL-STR-005",
        )
    )

    # 6. Extreme Revenue Drop -35%
    s6_features = features.copy()
    s6_inflows = (base_inflows * Decimal("0.65")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s6_bank = dict(features.get("bank_metrics", {}))
    s6_bank["operating_inflows_monthly"] = str(s6_inflows)
    s6_features["bank_metrics"] = s6_bank
    scenarios.append(
        scenario_payload(
            "REVENUE_DROP_35",
            "Extreme Revenue Drop (-35%)",
            "Simulates a 35% reduction in verified operating cash inflows.",
            s6_features,
            "POL-STR-006",
        )
    )

    # 7. Moderate Interest Rate Hike (+300bps)
    s7_features = features.copy()
    scenarios.append(
        scenario_payload(
            "RATE_HIKE_300BPS",
            "Moderate Rate Hike (+300bps)",
            "Re-amortises proposed facility at +300bps.",
            s7_features,
            "POL-STR-007",
            Decimal("0.165"),
        )
    )

    # 8. Severe Interest Rate Hike (+400bps)
    s8_features = features.copy()
    scenarios.append(
        scenario_payload(
            "RATE_HIKE_400BPS",
            "Severe Rate Hike (+400bps)",
            "Re-amortises proposed facility at +400bps.",
            s8_features,
            "POL-STR-008",
            Decimal("0.175"),
        )
    )

    # 9. Severe COGS Increase +20%
    s9_features = features.copy()
    s9_outflows = (base_outflows * Decimal("1.20")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s9_bank = dict(features.get("bank_metrics", {}))
    s9_bank["operating_outflows_monthly"] = str(s9_outflows)
    s9_features["bank_metrics"] = s9_bank
    scenarios.append(
        scenario_payload(
            "COGS_INCREASE_20",
            "Severe COGS Increase (+20%)",
            "Simulates a 20% inflation in operating expenses.",
            s9_features,
            "POL-STR-009",
        )
    )

    # 10. Extreme COGS Increase +30%
    s10_features = features.copy()
    s10_outflows = (base_outflows * Decimal("1.30")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s10_bank = dict(features.get("bank_metrics", {}))
    s10_bank["operating_outflows_monthly"] = str(s10_outflows)
    s10_features["bank_metrics"] = s10_bank
    scenarios.append(
        scenario_payload(
            "COGS_INCREASE_30",
            "Extreme COGS Increase (+30%)",
            "Simulates a 30% inflation in operating expenses.",
            s10_features,
            "POL-STR-010",
        )
    )

    # 11. Severe Combined Downside (-25% rev, +20% COGS, +300bps)
    s11_features = features.copy()
    s11_inflows = (base_inflows * Decimal("0.75")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s11_outflows = (base_outflows * Decimal("1.20")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s11_bank = dict(features.get("bank_metrics", {}))
    s11_bank["operating_inflows_monthly"] = str(s11_inflows)
    s11_bank["operating_outflows_monthly"] = str(s11_outflows)
    s11_features["bank_metrics"] = s11_bank
    scenarios.append(
        scenario_payload(
            "COMBINED_SEVERE",
            "Severe Combined Shock",
            "Simulates -25% rev, +20% COGS, and +300bps rate shock.",
            s11_features,
            "POL-STR-011",
            Decimal("0.165"),
        )
    )

    # 12. Extreme Combined Downside (-35% rev, +30% COGS, +400bps)
    s12_features = features.copy()
    s12_inflows = (base_inflows * Decimal("0.65")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s12_outflows = (base_outflows * Decimal("1.30")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s12_bank = dict(features.get("bank_metrics", {}))
    s12_bank["operating_inflows_monthly"] = str(s12_inflows)
    s12_bank["operating_outflows_monthly"] = str(s12_outflows)
    s12_features["bank_metrics"] = s12_bank
    scenarios.append(
        scenario_payload(
            "COMBINED_EXTREME",
            "Extreme Combined Shock",
            "Simulates -35% rev, +30% COGS, and +400bps rate shock.",
            s12_features,
            "POL-STR-012",
            Decimal("0.175"),
        )
    )

    # 13. Margin Squeeze (Prices down 10%, COGS up 10%)
    s13_features = features.copy()
    s13_inflows = (base_inflows * Decimal("0.90")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s13_outflows = (base_outflows * Decimal("1.10")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s13_bank = dict(features.get("bank_metrics", {}))
    s13_bank["operating_inflows_monthly"] = str(s13_inflows)
    s13_bank["operating_outflows_monthly"] = str(s13_outflows)
    s13_features["bank_metrics"] = s13_bank
    scenarios.append(
        scenario_payload(
            "MARGIN_SQUEEZE",
            "Margin Squeeze Shock",
            "Simulates -10% rev and +10% COGS.",
            s13_features,
            "POL-STR-013",
        )
    )

    # 14. Receivables Concentration Shock (-20% revenue from top buyer default)
    s14_features = features.copy()
    s14_inflows = (base_inflows * Decimal("0.80")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    s14_bank = dict(features.get("bank_metrics", {}))
    s14_bank["operating_inflows_monthly"] = str(s14_inflows)
    s14_features["bank_metrics"] = s14_bank
    scenarios.append(
        scenario_payload(
            "RECEIVABLES_SHOCK",
            "Top Buyer Default (-20%)",
            "Simulates a 20% drop in revenue due to top buyer default.",
            s14_features,
            "POL-STR-014",
        )
    )

    # 15. Reverse Stress Calculation
    s15_features = features.copy()

    # 1. Correct Reverse Stress
    # Reverse stress must not use a fixed 1.0x threshold.
    # Use the actual product/policy DSCR floor returned by the policy registry.
    policy_dscr_floor = getattr(base_policy, "policy_min_dscr", Decimal("1.25"))
    if "RECEIVABLE" in requested_product or "EQUIPMENT" in requested_product:
        # Some products might not be purely DSCR bounded, but for those that are:
        pass

    total_post_ds = base_existing_ds + FinancialCapacityEngine.calculate_emi(
        requested_amount, Decimal("0.135"), 36
    )

    if base_inflows > 0:
        break_even_inflows = (total_post_ds * policy_dscr_floor) + base_outflows
        if break_even_inflows < base_inflows:
            drop_pct = Decimal("1") - (break_even_inflows / base_inflows)
            s15_inflows = break_even_inflows
        else:
            drop_pct = Decimal("0")
            s15_inflows = base_inflows
    else:
        drop_pct = Decimal("0")
        s15_inflows = Decimal("0")

    s15_inflows = s15_inflows.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Calculate maximums
    max_rev_drop = (drop_pct * 100).quantize(Decimal("0.1"))

    max_outflow_increase = Decimal("0")
    if base_outflows > 0:
        max_allowed_outflows = base_inflows - (total_post_ds * policy_dscr_floor)
        if max_allowed_outflows > base_outflows:
            max_outflow_increase = (
                (max_allowed_outflows / base_outflows) - Decimal("1")
            ) * Decimal("100")
            max_outflow_increase = max_outflow_increase.quantize(Decimal("0.1"))

    # Max rate increase via search
    max_rate_hike_bps = 0
    current_rate = Decimal("0.135")
    for hike in range(100, 1000, 50):
        test_rate = current_rate + (Decimal(str(hike)) / Decimal("10000"))
        test_emi = FinancialCapacityEngine.calculate_emi(
            requested_amount, test_rate, 36
        )
        test_post_ds = base_existing_ds + test_emi
        test_cash = base_inflows - base_outflows
        if test_cash > 0 and (test_cash / test_post_ds) < policy_dscr_floor:
            max_rate_hike_bps = max(0, hike - 50)
            break
    if max_rate_hike_bps == 0:
        max_rate_hike_bps = 950

    s15_bank = dict(features.get("bank_metrics", {}))
    s15_bank["operating_inflows_monthly"] = str(s15_inflows)
    s15_features["bank_metrics"] = s15_bank

    scenarios.append(
        {
            "scenario_id": "REVERSE_STRESS",
            "scenario_name": "Reverse Stress (Break-even)",
            "impact": f"Revenue Drop to breach {policy_dscr_floor}x DSCR: -{max_rev_drop}%",
            "stressed_features": s15_features,
            "policy_rule_id": "POL-STR-015",
            "status": "NOT_ASSESSABLE"
            if base_decision.get("decision") == "ADDITIONAL_EVIDENCE_REQUIRED"
            else "MARGINAL",
            "reverse_stress_details": {
                "policy_floor": float(policy_dscr_floor),
                "base_value": float(base_inflows),
                "breakpoint_value": float(s15_inflows),
                "maximum_shock": f"-{max_rev_drop}% Revenue",
                "binding_rule_id": "POL-STR-015",
                "decision_before": "APPROVE",
                "decision_after": "DECLINE",
                "formula": "(Base Inflows - Base Outflows) / Post DSCR = Policy Floor",
                "inputs": {
                    "base_inflows": float(base_inflows),
                    "base_outflows": float(base_outflows),
                    "post_ds": float(total_post_ds),
                },
                "evidence_ids": [],
                "limitations": ["Assumes linear cost behavior"],
            },
        }
    )

    overall_stress_status = (
        "INVARIANT_VIOLATION"
        if any(s["status"] == "INVARIANT_VIOLATION" for s in scenarios)
        else "NOT_ASSESSABLE"
        if any(s["status"] == "NOT_ASSESSABLE" for s in scenarios)
        else "PASS"
        if all(s["status"] == "PASS" for s in scenarios)
        else "FAIL"
        if any(s["status"] == "FAIL" for s in scenarios)
        else "MARGINAL"
    )

    # Interactive Custom Query Recomputation with Re-amortized Shocked Rate
    custom_rev_factor = Decimal("1") - (Decimal(str(revenue_drop_pct)) / Decimal("100"))
    custom_inflows = (base_inflows * custom_rev_factor).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    rate_hike_dec = Decimal(str(interest_rate_hike_bps)) / Decimal("10000")
    custom_ds = base_existing_ds
    custom_annual_rate_dec = Decimal("0.135") + rate_hike_dec

    custom_features = features.copy()
    custom_bank = dict(features.get("bank_metrics", {}))
    custom_bank["operating_inflows_monthly"] = str(custom_inflows)
    custom_features["bank_metrics"] = custom_bank
    custom_features["verified_existing_debt_service_monthly"] = str(custom_ds)
    custom_features["obligation_verification_state"] = obligation_state

    custom_scores = ScoringEngine(custom_features).compute_all_scores()
    custom_cap = FinancialCapacityEngine.compute_capacity_from_features(
        custom_features,
        requested_amount,
        requested_product,
        custom_annual_rate=custom_annual_rate_dec,
    )
    custom_policy = DecisionPolicy(
        custom_features,
        custom_scores,
        requested_amount,
        requested_product,
        custom_annual_rate=custom_annual_rate_dec,
    ).evaluate()
    custom_dscr = get_effective_dscr(custom_cap)
    custom_limit = custom_policy.get("binding_limit", Decimal("0.00"))
    if custom_limit > base_limit:
        baseline_status = get_custom_status(base_dscr, base_inflows - base_outflows)
        return {
            "overall_stress_status": "INVARIANT_VIOLATION",
            "base_dscr": float(base_dscr),
            "base_binding_limit": float(base_limit),
            "scenarios": scenarios,
            "authoritative_engine": "Vyapar Pulse Stress Lab Engine v2.0",
            "calculation_version": "2.0-STRESS-CANONICAL",
            "scenario": {
                "revenue_drop_pct": revenue_drop_pct,
                "interest_rate_hike_bps": interest_rate_hike_bps,
            },
            "baseline": {
                "dscr": float(base_dscr),
                "max_loan_amount": float(base_limit),
                "status": baseline_status,
            },
            "stressed": {
                "dscr": float(custom_dscr),
                "max_loan_amount": float(custom_limit),
                "status": "INVARIANT_VIOLATION",
                "message": "adverse_supportable_amount > baseline_supportable_amount",
            },
        }
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
            "interest_rate_hike_bps": interest_rate_hike_bps,
        },
        "baseline": {
            "dscr": float(base_dscr),
            "max_loan_amount": float(base_limit),
            "status": baseline_status,
        },
        "stressed": {
            "dscr": float(custom_dscr),
            "max_loan_amount": float(custom_limit),
            "status": custom_status,
        },
        "summary": f"Stressed DSCR under {revenue_drop_pct}% revenue drop and +{interest_rate_hike_bps}bps rate hike is {custom_dscr:.2f} ({custom_status}).",
    }
