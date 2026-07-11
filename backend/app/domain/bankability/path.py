import copy
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.policy import DecisionPolicy
from app.core.scoring.scorer import ScoringEngine
from app.domain.financial.engine import FinancialCapacityEngine


def compute_bankability_path(
    features: Dict[str, Any],
    scores: Dict[str, Any],
    requested_amount: Decimal,
    requested_product: str,
    target_amount: Optional[float] = None
) -> Dict[str, Any]:
    """
    Authoritative step-by-step Bankability Path generation engine.
    Executes real same-engine simulation (before/after recomputation across ScoringEngine,
    DecisionPolicy, and FinancialCapacityEngine) for 30-day, 60-day, and 90-day milestones.
    """
    base_policy = DecisionPolicy(features, scores, requested_amount, requested_product)
    base_decision = base_policy.evaluate()
    current_state = base_decision.get("decision", "DECLINE")
    current_limit = base_decision.get("binding_limit", Decimal("0"))
    if not isinstance(current_limit, Decimal):
        current_limit = Decimal(str(current_limit))
    
    evidence_score = Decimal(str(scores.get("evidence_confidence_score") or 0))
    health_score = scores.get("financial_health_index", scores.get("financial_health_score"))
    health_score = Decimal(str(health_score)) if health_score is not None else None
    base_cap = FinancialCapacityEngine.compute_capacity_from_features(features, requested_amount, requested_product)
    base_dscr = base_cap.get("post_loan_dscr") or base_cap.get("current_dscr")
    milestones = []

    def numeric(value: Any) -> Optional[float]:
        return None if value is None else float(Decimal(str(value)))

    def run_sim(milestone_id: str, tier: str, action: str, hindi_action: str, changed_input: str, assumption: str, sim_features: Dict[str, Any], days: int) -> Dict[str, Any]:
        sim_scores = ScoringEngine(sim_features).compute_all_scores()
        sim_decision = DecisionPolicy(sim_features, sim_scores, requested_amount, requested_product).evaluate()
        sim_cap = FinancialCapacityEngine.compute_capacity_from_features(sim_features, requested_amount, requested_product)
        after_limit = Decimal(str(sim_decision.get("binding_limit", 0) or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        after_health = sim_scores.get("financial_health_index")
        after_dscr = sim_cap.get("post_loan_dscr") or sim_cap.get("current_dscr")
        impact_known = after_health is not None and after_dscr is not None
        return {
            "milestone_id": milestone_id,
            "timeline_tier": tier,
            "action": action,
            "hindi_action": hindi_action,
            "changed_input": changed_input,
            "assumption": assumption,
            "impact_on_score": "IMPACT_NOT_QUANTIFIABLE" if not impact_known else f"FHI {health_score} -> {after_health}; Credit Health {scores.get('vyapar_credit_health_score')} -> {sim_scores.get('vyapar_credit_health_score')}",
            "expected_timeline_days": days,
            "target_state": sim_decision.get("decision", "ADDITIONAL_EVIDENCE_REQUIRED"),
            "target_tier": "SCENARIO_ONLY",
            "projected_limit_inr": float(after_limit),
            "projected_rate_bps": None,
            "prerequisites": [assumption],
            "scenario_disclaimer": "Scenario only. Completion does not guarantee sanction.",
            "simulation_evidence": {
                "before_evidence_score": float(evidence_score),
                "after_evidence_score": numeric(sim_scores.get("evidence_confidence_score")),
                "before_health_score": numeric(health_score),
                "after_health_score": numeric(after_health),
                "before_fhi": numeric(health_score),
                "after_fhi": numeric(after_health),
                "before_credit_health_score": scores.get("vyapar_credit_health_score"),
                "after_credit_health_score": sim_scores.get("vyapar_credit_health_score"),
                "before_dscr": numeric(base_dscr),
                "after_dscr": numeric(after_dscr),
                "before_supportable_amount": float(current_limit),
                "after_supportable_amount": float(after_limit),
                "before_policy_state": current_state,
                "after_policy_state": sim_decision.get("decision"),
            },
        }

    if features.get("consent_status") != "VALID":
        sim_features = copy.deepcopy(features)
        sim_features["consent_status"] = "VALID"
        milestones.append(run_sim(
            "MIL-001", "30_DAYS",
            "Obtain valid borrower consent and governed bank evidence before assessment",
            "मूल्यांकन से पहले वैध सहमति और सत्यापित बैंक साक्ष्य प्राप्त करें",
            "consent_status", "Consent is valid and evidence rails are refreshed; no financial values are fabricated.",
            sim_features, 30,
        ))

    if base_cap.get("obligation_verification_state") != "VERIFIED":
        sim_features = copy.deepcopy(features)
        sim_features["obligation_verification_state"] = "VERIFIED"
        sim_features["verified_existing_debt_service_monthly"] = sim_features.get("verified_existing_debt_service_monthly", "0")
        milestones.append(run_sim(
            "MIL-002", "45_DAYS",
            "Verify existing obligations through bureau report or authoritative debt-service evidence",
            "ब्यूरो रिपोर्ट या अधिकृत ऋण-सेवा साक्ष्य से मौजूदा देनदारियां सत्यापित करें",
            "obligation_verification_state", "Only the verification state changes; debt amount remains the recorded value.",
            sim_features, 45,
        ))

    bank = features.get("bank_metrics", {})
    inflows = Decimal(str(bank.get("operating_inflows_monthly", "0") or 0))
    outflows = Decimal(str(bank.get("operating_outflows_monthly", "0") or 0))
    if current_state not in ("APPROVE", "READY_FOR_REVIEW") and inflows > 0 and outflows > 0:
        sim_features = copy.deepcopy(features)
        sim_bank = sim_features.setdefault("bank_metrics", {})
        sim_bank["operating_outflows_monthly"] = str((outflows * Decimal("0.95")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        milestones.append(run_sim(
            "MIL-003", "60_DAYS",
            "Reduce verified operating expenses by 5% through supplier/payment discipline",
            "सप्लायर और भुगतान अनुशासन से सत्यापित परिचालन खर्च 5% घटाएं",
            "operating_outflows_monthly", "Scenario reduces only measured operating outflows by 5%.",
            sim_features, 60,
        ))

    current_cycle = features.get("working_capital_metrics", {}).get("operating_cycle_days", features.get("operating_cycle_days"))
    if current_state not in ("APPROVE", "READY_FOR_REVIEW") and current_cycle is not None:
        sim_features = copy.deepcopy(features)
        sim_features.setdefault("working_capital_metrics", {})["operating_cycle_days"] = str(max(Decimal("30"), Decimal(str(current_cycle)) - Decimal("15")))
        milestones.append(run_sim(
            "MIL-004", "90_DAYS",
            "Reduce operating cycle by 15 days through receivables collection discipline",
            "प्राप्य वसूली अनुशासन से परिचालन चक्र 15 दिन घटाएं",
            "operating_cycle_days", "Scenario reduces only the measured operating cycle, floored at 30 days.",
            sim_features, 90,
        ))

    if not milestones and current_state in ("APPROVE", "READY_FOR_REVIEW"):
        milestones.append({
            "milestone_id": "MIL-OPT",
            "timeline_tier": "30_DAYS",
            "action": "Enable escrow account routing and quarterly automated credit twin monitoring",
            "hindi_action": "एस्क्रो खाता रूटिंग और त्रैमासिक स्वचालित क्रेडिट ट्विन निगरानी सक्षम करें",
            "impact_on_score": "IMPACT_NOT_QUANTIFIABLE",
            "expected_timeline_days": 30,
            "target_state": current_state,
            "target_tier": "MONITORING",
            "projected_limit_inr": float(current_limit),
            "projected_rate_bps": None,
            "prerequisites": ["Institutional escrow mandates"],
            "scenario_disclaimer": "Scenario only. Completion does not guarantee sanction.",
            "simulation_evidence": {
                "before_evidence_score": float(evidence_score),
                "after_evidence_score": float(evidence_score),
                "before_health_score": numeric(health_score),
                "after_health_score": numeric(health_score),
                "before_dscr": numeric(base_dscr),
                "after_dscr": numeric(base_dscr)
            }
        })

    tgt_req = float(target_amount) if target_amount is not None else float(requested_amount)
    curr_lim_flt = float(current_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    gap = max(0.0, tgt_req - curr_lim_flt)
    max_achievable = max([m.get("projected_limit_inr", 0.0) for m in milestones] + [curr_lim_flt])

    hindi_presentation = {
        "summary": "बैंक योग्यता पथ (Bankability Path): यह दस्तावेज़ आवेदक को स्पष्ट और चरणबद्ध कार्रवाई योजना प्रदान करता है जिससे वे अपनी ऋण योग्यता और स्वीकृत सीमा को बढ़ा सकते हैं।",
        "milestone_actions": [m.get("hindi_action", m.get("action", "")) for m in milestones]
    }

    return {
        "current_state": current_state,
        "current_binding_limit": curr_lim_flt,
        "current_limit": curr_lim_flt,
        "target_requested": tgt_req,
        "gap_to_target": gap,
        "is_target_achievable_now": curr_lim_flt >= tgt_req,
        "max_achievable_limit": max_achievable,
        "current_evidence_score": float(evidence_score),
        "current_health_score": numeric(health_score),
        "milestones": milestones,
        "hindi_bilingual_presentation": hindi_presentation,
        "engine_version": "2.0-BANKABILITY-CANONICAL"
    }


def simulate_bankability_variable(
    features: Dict[str, Any],
    scores: Dict[str, Any],
    requested_amount: Decimal,
    requested_product: str,
    overrides: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Bankability Simulation Engine.
    Replaces static/template uplift values with custom variable simulations across any feature/financial parameter.
    Computes exact before vs after scores, limits, DSCR, and decision outcomes using the canonical engines.
    """
    base_policy = DecisionPolicy(features, scores, requested_amount, requested_product)
    base_decision = base_policy.evaluate()
    try:
        base_cap = FinancialCapacityEngine.compute_capacity_from_features(features, requested_amount, requested_product)
    except Exception:
        base_cap = {"supportable_limit_inr": str(base_decision.get("binding_limit", 0)), "verified_dscr": str(features.get("bank_metrics", {}).get("dscr", "1.0"))}

    sim_features = copy.deepcopy(features)
    bank_sim = sim_features.setdefault("bank_metrics", {})
    recon_sim = sim_features.setdefault("reconciliation_metrics", {})
    wc_sim = sim_features.setdefault("working_capital_metrics", {})
    gst_sim = sim_features.setdefault("gst_metrics", {})

    if "dscr" in overrides and overrides["dscr"] is not None:
        bank_sim["dscr"] = str(overrides["dscr"])
    if "operating_inflows_monthly" in overrides and overrides["operating_inflows_monthly"] is not None:
        bank_sim["operating_inflows_monthly"] = str(overrides["operating_inflows_monthly"])
    if "operating_outflows_monthly" in overrides and overrides["operating_outflows_monthly"] is not None:
        bank_sim["operating_outflows_monthly"] = str(overrides["operating_outflows_monthly"])
    if "gst_bank_ratio" in overrides and overrides["gst_bank_ratio"] is not None:
        recon_sim["gst_bank_ratio"] = str(overrides["gst_bank_ratio"])
    if "operating_cycle_days" in overrides and overrides["operating_cycle_days"] is not None:
        wc_sim["operating_cycle_days"] = str(overrides["operating_cycle_days"])
        sim_features["operating_cycle_days"] = str(overrides["operating_cycle_days"])
    if "verified_existing_debt_service_monthly" in overrides and overrides["verified_existing_debt_service_monthly"] is not None:
        sim_features["verified_existing_debt_service_monthly"] = str(overrides["verified_existing_debt_service_monthly"])
    if "consent_status" in overrides and overrides["consent_status"] is not None:
        sim_features["consent_status"] = str(overrides["consent_status"])
    if "obligation_verification_state" in overrides and overrides["obligation_verification_state"] is not None:
        sim_features["obligation_verification_state"] = str(overrides["obligation_verification_state"])
    if "months_filed" in overrides and overrides["months_filed"] is not None:
        bank_sim["months_filed"] = int(overrides["months_filed"])
        gst_sim["months_filed"] = int(overrides["months_filed"])

    sim_scorer = ScoringEngine(sim_features)
    sim_scores = sim_scorer.compute_all_scores()
    sim_policy = DecisionPolicy(sim_features, sim_scores, requested_amount, requested_product)
    sim_decision = sim_policy.evaluate()
    try:
        sim_cap = FinancialCapacityEngine.compute_capacity_from_features(sim_features, requested_amount, requested_product)
    except Exception:
        sim_cap = {"supportable_limit_inr": str(sim_decision.get("binding_limit", 0)), "verified_dscr": str(bank_sim.get("dscr", "1.0"))}

    before_limit = float(Decimal(str(base_decision.get("binding_limit", 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    after_limit = float(Decimal(str(sim_decision.get("binding_limit", 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def dec_or_none(value: Any) -> Optional[Decimal]:
        return None if value is None else Decimal(str(value))

    before_health_dec = dec_or_none(scores.get("financial_health_score"))
    after_health_dec = dec_or_none(sim_scores.get("financial_health_score"))
    before_fhi_dec = dec_or_none(scores.get("financial_health_index"))
    after_fhi_dec = dec_or_none(sim_scores.get("financial_health_index"))

    before_health = float(before_health_dec) if before_health_dec is not None else None
    after_health = float(after_health_dec) if after_health_dec is not None else None
    before_fhi = float(before_fhi_dec) if before_fhi_dec is not None else None
    after_fhi = float(after_fhi_dec) if after_fhi_dec is not None else None

    before_credit = scores.get("vyapar_credit_health_score")
    after_credit = sim_scores.get("vyapar_credit_health_score")

    try:
        base_dscr_value = base_cap.get("post_loan_dscr") or base_cap.get("current_dscr")
        before_dscr = None if base_dscr_value is None else float(Decimal(str(base_dscr_value)))
    except Exception:
        before_dscr = None
    try:
        sim_dscr_value = sim_cap.get("post_loan_dscr") or sim_cap.get("current_dscr")
        after_dscr = None if sim_dscr_value is None else float(Decimal(str(sim_dscr_value)))
    except Exception:
        after_dscr = None

    return {
        "before_simulation": {
            "decision": base_decision.get("decision", "DECLINE"),
            "binding_limit_inr": before_limit,
            "financial_health_score": before_health,
            "financial_health_index": before_fhi,
            "vyapar_credit_health_score": before_credit,
            "verified_dscr": before_dscr,
            "offers": base_decision.get("offers", [])
        },
        "after_simulation": {
            "decision": sim_decision.get("decision", "DECLINE"),
            "binding_limit_inr": after_limit,
            "financial_health_score": after_health,
            "financial_health_index": after_fhi,
            "vyapar_credit_health_score": after_credit,
            "verified_dscr": after_dscr,
            "offers": sim_decision.get("offers", [])
        },
        "uplift_summary": {
            "limit_uplift_inr": max(0.0, after_limit - before_limit),
            "health_score_uplift": None if after_health is None or before_health is None else after_health - before_health,
            "fhi_uplift": None if after_fhi is None or before_fhi is None else after_fhi - before_fhi,
            "credit_score_uplift": None if after_credit is None or before_credit is None else after_credit - before_credit,
            "dscr_uplift": None if after_dscr is None or before_dscr is None else after_dscr - before_dscr
        },
        "simulated_overrides": overrides,
        "engine_version": "2.0-BANKABILITY-SIMULATION"
    }
