from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.policy import DecisionPolicy


def compute_bankability_path(features: Dict[str, Any], scores: Dict[str, Any], requested_amount: Decimal, requested_product: str, target_amount: float = None) -> Dict[str, Any]:
    """
    Authoritative step-by-step Bankability Path generation engine.
    Calculates exact milestone actions, score impacts, target states, projected limits, tiers, and pricing.
    """
    base_policy = DecisionPolicy(features, scores, requested_amount, requested_product)
    base_decision = base_policy.evaluate()
    current_state = base_decision.get("decision", "DECLINE")
    current_limit = base_decision.get("binding_limit", Decimal("0"))
    
    evidence_score = scores.get("evidence_confidence_score", 50.0)
    health_score = scores.get("financial_health_score", 50.0)
    consent_status = features.get("consent_status", "PENDING")
    
    milestones = []
    
    # Check what missing evidence or financial optimizations can elevate the case
    if consent_status != "VALID" or evidence_score < 75.0:
        milestones.append({
            "milestone_id": "MIL-001",
            "action": "Complete live Account Aggregator (AA) sync for 12 months bank statement feed",
            "hindi_action": "12 महीनों के बैंक विवरण फीड के लिए लाइव अकाउंट एग्रीगेटर (AA) सिंक पूरा करें",
            "impact_on_score": "+20 points on Evidence Confidence Score",
            "expected_timeline_days": 3,
            "target_state": "CONDITIONAL_OFFER" if current_state == "DECLINE" else "APPROVE",
            "target_tier": "CONSERVATIVE" if current_limit == 0 else "BALANCED",
            "projected_limit_inr": float((requested_amount * Decimal("0.60")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if current_limit == 0 else float((current_limit * Decimal("1.25")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "projected_rate_bps": 1350,  # 13.50% p.a.
            "prerequisites": ["Valid digital signature / AA consent PIN"]
        })
        
    if not features.get("gst_metrics", {}).get("avg_monthly_revenue") or evidence_score < 85.0:
        milestones.append({
            "milestone_id": "MIL-002",
            "action": "File and reconcile past 4 quarters GST GSTR-1 and GSTR-3B returns",
            "hindi_action": "पिछले 4 तिमाहियों के GST GSTR-1 और GSTR-3B रिटर्न दाखिल करें और उनका मिलान करें",
            "impact_on_score": "+15 points on Evidence Confidence Score & +10 points on Financial Health Score",
            "expected_timeline_days": 14,
            "target_state": "APPROVE",
            "target_tier": "BALANCED",
            "projected_limit_inr": float((current_limit * Decimal("1.33")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if current_limit > 0 else float((requested_amount * Decimal("0.80")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "projected_rate_bps": 1300,  # 13.00% p.a.
            "prerequisites": ["GSTIN credential sync"]
        })

    if health_score < 80.0 or current_state in ("DECLINE", "CONDITIONAL_OFFER"):
        milestones.append({
            "milestone_id": "MIL-003",
            "action": "Maintain average monthly bank account balance >= INR 3,000,000 for 60 consecutive days",
            "hindi_action": "60 लगातार दिनों के लिए औसत मासिक बैंक खाता शेष ≥ ₹30,00,000 बनाए रखें",
            "impact_on_score": "+18 points on Financial Health Score (Liquidity buffer expansion)",
            "expected_timeline_days": 60,
            "target_state": "APPROVE",
            "target_tier": "GROWTH",
            "projected_limit_inr": float(requested_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "projected_rate_bps": 1250,  # 12.50% p.a.
            "prerequisites": ["MIL-001 completion"]
        })

    if not milestones and current_state == "APPROVE":
        milestones.append({
            "milestone_id": "MIL-OPT",
            "action": "Enable escrow account routing and quarterly automated credit twin monitoring",
            "hindi_action": "एस्क्रो खाता रूटिंग और त्रैमासिक स्वचालित क्रेडिट ट्विन निगरानी सक्षम करें",
            "impact_on_score": "+5 points on Evidence Confidence Score",
            "expected_timeline_days": 7,
            "target_state": "APPROVE",
            "target_tier": "GROWTH",
            "projected_limit_inr": float((current_limit * Decimal("1.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "projected_rate_bps": 1200,  # 12.00% p.a. prime institutional rate
            "prerequisites": ["Institutional escrow mandates"]
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
        "current_evidence_score": evidence_score,
        "current_health_score": health_score,
        "milestones": milestones,
        "hindi_bilingual_presentation": hindi_presentation,
        "engine_version": "2.0-BANKABILITY-CANONICAL"
    }
