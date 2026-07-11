#!/usr/bin/env python3
"""
generate_inclusion_impact_report.py — P1: 500-MSME Deterministic Cohort Inclusion Impact Generator

Generates a deterministic 500-MSME Indian cohort across diverse segments, tiers, and demographics.
Runs full assessment through `ScoringEngine` (FHI & Vyapar Credit Health Score), `DecisionPolicy`, and `FinancialCapacityEngine`.
Quantifies credit inclusion impact relative to traditional bureau/collateral-only underwriting models.
Outputs exact metrics to artifacts/inclusion_impact_report.json.
"""

import os
import sys
import json
import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List

# Ensure app imports work from project root / backend directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.domain.financial.engine import FinancialCapacityEngine
from app.db.orm.cases import SystemRecommendation
from app.core.versions import POLICY_VERSION, CALCULATION_VERSION


def generate_cohort(cohort_size: int = 500) -> List[Dict[str, Any]]:
    segments = [
        ("Precision Manufacturing", "Tier 1 Urban", False),
        ("Seasonal Agri-Processing", "Tier 2 Semi-Urban", True),
        ("Textile & Garments", "Tier 2 Semi-Urban", False),
        ("Retail Trade & Kirana", "Tier 3 Rural / Micro", False),
        ("IT & Tech Services", "Tier 1 Urban", False),
        ("Logistics & Transport", "Tier 2 Semi-Urban", False),
        ("Food & Beverage Processing", "Tier 3 Rural / Micro", True),
        ("Micro Artisan & Craft Vendors", "Tier 3 Rural / Micro", True),
        ("Electronics Assembly & Components", "Tier 1 Urban", False),
        ("Healthcare & Diagnostics Clinics", "Tier 2 Semi-Urban", False),
    ]

    cohort = []
    for i in range(1, cohort_size + 1):
        seg_idx = (i - 1) % len(segments)
        seg_name, tier, is_seasonal = segments[seg_idx]

        # Deterministic variation
        base_turnover = Decimal("1500000") + Decimal((i * 123457) % 85000000)
        inflows_monthly = (base_turnover / Decimal("12")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        
        # Varying DSCR deterministically between 0.85 and 2.65
        dscr_raw = Decimal("0.85") + Decimal(((i * 31) % 180) / 100.0)
        dscr = dscr_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Operating debits and verified debt service
        # Realistic business operating expenses (approx 70-80% of revenue)
        debits_monthly = (inflows_monthly * Decimal("0.75")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        operating_cash_available = inflows_monthly - debits_monthly

        # Verified existing debt service based on dscr target
        if dscr > Decimal("0") and (i % 5 != 0):
            verified_ds = (operating_cash_available / dscr).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        else:
            verified_ds = Decimal("0")

        # Operating cycle days
        cycle_days = 30 + ((i * 13) % 90)

        # GST bank ratio
        ratio = Decimal("0.88") + Decimal(((i * 7) % 30) / 100.0)
        ratio = ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Demographics & Inclusion flags
        is_women_owned = ((i % 3) == 0)
        is_ntc_thin_file = ((i % 4) == 0) or tier == "Tier 3 Rural / Micro"
        has_digital_commerce = ((i % 2) == 0) or seg_name in ("Retail Trade & Kirana", "Textile & Garments")

        features = {
            "consent_status": "VALID",
            "integrity_flag": False,
            "bank_metrics": {
                "dscr": str(dscr),
                "operating_inflows_monthly": str(inflows_monthly),
                "operating_outflows_monthly": str(debits_monthly),
                "avg_monthly_credits": str(inflows_monthly),
                "avg_monthly_debits": str(debits_monthly),
            },
            "gst_metrics": {
                "months_filed": 18 if not is_ntc_thin_file else 12,
                "avg_monthly_revenue": str(inflows_monthly),
                "trend": "GROWING" if (i % 2 == 0) else "STABLE"
            },
            "reconciliation_metrics": {
                "gst_bank_ratio": str(ratio),
            },
            "working_capital_metrics": {
                "operating_cycle_days": str(cycle_days),
            },
            "obligation_verification_state": "VERIFIED" if (i % 5 != 0) else "UNKNOWN_OBLIGATIONS",
            "verified_existing_debt_service_monthly": str(verified_ds),
            "invoice_metrics": {
                "total_invoices": 24 if not is_ntc_thin_file else 12,
                "avg_payment_delay_days": "15",
                "eligible_amount": str(inflows_monthly * Decimal("3")),
            },
            "authoritative_evidence_ids": [f"EVID-COHORT-{i}"],
            "demographic_tags": {
                "women_owned_or_led": is_women_owned,
                "new_to_credit_or_thin_file": is_ntc_thin_file,
                "seasonal_cash_flow": is_seasonal,
                "digital_commerce_enabled": has_digital_commerce,
            }
        }

        requested_amount = (inflows_monthly * Decimal("4")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        cohort.append({
            "msme_id": f"MSME-COHORT-2026-{i:04d}",
            "segment": seg_name,
            "tier": tier,
            "features": features,
            "requested_amount": requested_amount,
            "demographics": features["demographic_tags"]
        })

    return cohort


def evaluate_cohort(cohort: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_evaluated = len(cohort)
    decisions_count = {
        SystemRecommendation.READY_FOR_REVIEW.value: 0,
        SystemRecommendation.CONDITIONAL_OFFER.value: 0,
        SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value: 0,
        SystemRecommendation.ENHANCED_DUE_DILIGENCE.value: 0,
        SystemRecommendation.DECLINE_RECOMMENDED.value: 0,
    }

    tier_breakdown = {}
    segment_breakdown = {}
    demographic_impact = {
        "women_owned_or_led": {"total": 0, "included": 0, "unlocked_inr": Decimal("0")},
        "new_to_credit_or_thin_file": {"total": 0, "included": 0, "unlocked_inr": Decimal("0")},
        "seasonal_cash_flow": {"total": 0, "included": 0, "unlocked_inr": Decimal("0")},
        "digital_commerce_enabled": {"total": 0, "included": 0, "unlocked_inr": Decimal("0")},
    }

    traditional_rejected_or_unassessed_count = 0
    vyapar_pulse_included_count = 0
    total_credit_unlocked_inr = Decimal("0")

    total_fhi = Decimal("0")
    total_credit_score = 0

    evaluated_profiles = []

    for item in cohort:
        features = item["features"]
        req_amt = item["requested_amount"]
        tier = item["tier"]
        seg = item["segment"]
        demos = item["demographics"]

        # 1. Scoring Engine
        scorer = ScoringEngine(features)
        scores = scorer.compute_all_scores()
        fhi = scores["financial_health_index"]
        credit_score = scores["vyapar_credit_health_score"]

        total_fhi += Decimal(str(fhi))
        total_credit_score += credit_score

        # 2. Capacity Engine
        capacity = FinancialCapacityEngine.compute_capacity_from_features(features)
        limit_inr = Decimal(str(capacity.get("binding_product_limit", capacity.get("supportable_limit_inr", Decimal("0")))))

        # 3. Decision Policy
        policy = DecisionPolicy(features, scores, req_amt, "WORKING_CAPITAL_LINE")
        decision_result = policy.evaluate()
        dec_value = decision_result["decision"]
        decisions_count[dec_value] = decisions_count.get(dec_value, 0) + 1

        # Traditional bureau/collateral criteria: requires DSCR >= 1.33 AND not thin file AND verified obligations
        dscr = Decimal(features["bank_metrics"]["dscr"])
        is_ntc = demos["new_to_credit_or_thin_file"]
        is_traditionally_rejected = (dscr < Decimal("1.33") or is_ntc or features["obligation_verification_state"] != "VERIFIED")

        if is_traditionally_rejected:
            traditional_rejected_or_unassessed_count += 1
            if dec_value in (SystemRecommendation.READY_FOR_REVIEW.value, SystemRecommendation.CONDITIONAL_OFFER.value):
                vyapar_pulse_included_count += 1
                total_credit_unlocked_inr += limit_inr
            elif dec_value in (SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value, SystemRecommendation.ENHANCED_DUE_DILIGENCE.value):
                # Bankability path also provides structured inclusion roadmap
                vyapar_pulse_included_count += 1

        # Track demographics
        for demo_key, demo_val in demos.items():
            if demo_val:
                demographic_impact[demo_key]["total"] += 1
                if dec_value in (SystemRecommendation.READY_FOR_REVIEW.value, SystemRecommendation.CONDITIONAL_OFFER.value, SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value, SystemRecommendation.ENHANCED_DUE_DILIGENCE.value):
                    demographic_impact[demo_key]["included"] += 1
                    if dec_value in (SystemRecommendation.READY_FOR_REVIEW.value, SystemRecommendation.CONDITIONAL_OFFER.value):
                        demographic_impact[demo_key]["unlocked_inr"] += limit_inr

        # Track Tier
        if tier not in tier_breakdown:
            tier_breakdown[tier] = {"total": 0, "ready_or_conditional": 0, "bankability_path": 0, "total_limit_inr": Decimal("0")}
        tier_breakdown[tier]["total"] += 1
        if dec_value in (SystemRecommendation.READY_FOR_REVIEW.value, SystemRecommendation.CONDITIONAL_OFFER.value):
            tier_breakdown[tier]["ready_or_conditional"] += 1
            tier_breakdown[tier]["total_limit_inr"] += limit_inr
        elif dec_value in (SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value, SystemRecommendation.ENHANCED_DUE_DILIGENCE.value):
            tier_breakdown[tier]["bankability_path"] += 1

        # Track Segment
        if seg not in segment_breakdown:
            segment_breakdown[seg] = {"total": 0, "ready_or_conditional": 0, "bankability_path": 0, "total_limit_inr": Decimal("0")}
        segment_breakdown[seg]["total"] += 1
        if dec_value in (SystemRecommendation.READY_FOR_REVIEW.value, SystemRecommendation.CONDITIONAL_OFFER.value):
            segment_breakdown[seg]["ready_or_conditional"] += 1
            segment_breakdown[seg]["total_limit_inr"] += limit_inr
        elif dec_value in (SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value, SystemRecommendation.ENHANCED_DUE_DILIGENCE.value):
            segment_breakdown[seg]["bankability_path"] += 1

        if len(evaluated_profiles) < 10:  # Sample profiles
            evaluated_profiles.append({
                "msme_id": item["msme_id"],
                "segment": seg,
                "tier": tier,
                "dscr": float(dscr),
                "fhi": float(fhi),
                "vyapar_credit_health_score": credit_score,
                "decision": dec_value,
                "supportable_limit_inr": float(limit_inr)
            })

    # Final formatting
    avg_fhi = float((total_fhi / Decimal(str(total_evaluated))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    avg_credit_score = int(round(total_credit_score / total_evaluated))

    inclusion_rate_pct = float((Decimal(vyapar_pulse_included_count) / Decimal(traditional_rejected_or_unassessed_count) * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) if traditional_rejected_or_unassessed_count > 0 else 100.0

    return {
        "report_title": "Vyapar Pulse RC3 — 500-MSME Deterministic Cohort Inclusion Impact Report",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "policy_version": POLICY_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "cohort_size": total_evaluated,
        "executive_summary": {
            "total_msmes_evaluated": total_evaluated,
            "traditional_rejected_or_unassessed_count": traditional_rejected_or_unassessed_count,
            "vyapar_pulse_included_count": vyapar_pulse_included_count,
            "inclusion_rate_pct": inclusion_rate_pct,
            "total_credit_unlocked_inr": float(total_credit_unlocked_inr),
            "avg_financial_health_index": avg_fhi,
            "avg_vyapar_credit_health_score": avg_credit_score,
        },
        "decision_distribution": decisions_count,
        "tier_breakdown": {
            k: {
                "total": v["total"],
                "ready_or_conditional": v["ready_or_conditional"],
                "bankability_path": v["bankability_path"],
                "total_limit_inr": float(v["total_limit_inr"]),
            } for k, v in tier_breakdown.items()
        },
        "segment_breakdown": {
            k: {
                "total": v["total"],
                "ready_or_conditional": v["ready_or_conditional"],
                "bankability_path": v["bankability_path"],
                "total_limit_inr": float(v["total_limit_inr"]),
            } for k, v in segment_breakdown.items()
        },
        "demographic_inclusion_impact": {
            k: {
                "total_msmes": v["total"],
                "included_msmes": v["included"],
                "inclusion_pct": float((Decimal(v["included"]) / Decimal(v["total"]) * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) if v["total"] > 0 else 0.0,
                "unlocked_limit_inr": float(v["unlocked_inr"]),
            } for k, v in demographic_impact.items()
        },
        "sample_evaluated_profiles": evaluated_profiles
    }


def main():
    cohort = generate_cohort(500)
    report = evaluate_cohort(cohort)

    out_path = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "inclusion_impact_report.json")
    out_path = os.path.abspath(out_path)
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"✅ Successfully generated 500-MSME Inclusion Impact Report at {out_path}")
    print(f"   Evaluated: {report['cohort_size']} MSMEs")
    print(f"   Traditional Unassessed/Rejected: {report['executive_summary']['traditional_rejected_or_unassessed_count']}")
    print(f"   Vyapar Pulse Included: {report['executive_summary']['vyapar_pulse_included_count']} ({report['executive_summary']['inclusion_rate_pct']}%)")
    print(f"   Total Credit Unlocked: INR {report['executive_summary']['total_credit_unlocked_inr']:,.2f}")


if __name__ == "__main__":
    main()
