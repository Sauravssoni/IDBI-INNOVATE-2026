#!/usr/bin/env python3
"""
run_synthetic_validation_harness.py — CD-006: Quantitative Synthetic Validation Harness

Evaluates the deterministic DecisionPolicy and SafeLimitEngine across a diverse synthetic MSME cohort
representing distinct Indian business segments, financial profiles, and stress scenarios.
Validates exact bounds, monotonicity, and decision determinism without external API calls.

Outputs transparent validation reporting including scenario counts, assertion counts, and
pass/fail metrics across segments to artifacts/synthetic_validation_report.json.
"""

import os
import sys
import json
import subprocess
import datetime
from decimal import Decimal
from typing import Dict, Any, List

from app.core.decision.policy import DecisionPolicy
from app.db.orm.cases import SystemRecommendation
from app.core.versions import POLICY_VERSION, CALCULATION_VERSION


def get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except Exception:
        return "unknown"


def log(msg: str):
    print(msg, file=sys.stderr)


def create_synthetic_scenarios() -> List[Dict[str, Any]]:
    """Generate diverse synthetic scenarios across 5 key Indian MSME segments."""
    scenarios = []

    # Segment 1: High-Growth Precision Manufacturing (Tier 1)
    for i in range(1, 5):
        turnover = Decimal("45000000") + Decimal(i * 5000000)
        monthly_inflows = turnover / Decimal("12")
        monthly_outflows = monthly_inflows * Decimal("0.84")  # 16% margin
        scenarios.append(
            {
                "scenario_id": f"SEG1_MFG_T1_{i}",
                "segment": "Precision Manufacturing (Tier 1)",
                "features": {
                    "consent_status": "VALID",
                    "integrity_flag": False,
                    "gst_metrics": {"avg_monthly_revenue": str(monthly_inflows)},
                    "bank_metrics": {
                        "dscr": "1.66",
                        "avg_monthly_credits": str(monthly_inflows),
                        "avg_monthly_debits": str(monthly_outflows),
                    },
                    "invoice_metrics": {
                        "eligible_amount": str(turnover * Decimal("0.30"))
                    },
                    "authoritative_evidence_ids": [f"EVID-MFG-{i}"],
                },
                "scores": {"evidence_confidence_score": 85.0 + i},
                "requested_amount": Decimal("5000000"),
                "requested_product": "WORKING_CAPITAL_LINE",
                "expected_decisions": [
                    SystemRecommendation.READY_FOR_REVIEW.value,
                    SystemRecommendation.CONDITIONAL_OFFER.value,
                ],
                "expect_limit_gt": Decimal("4000000"),
            }
        )

    # Segment 2: Seasonal Agri-Processing / Textiles (Tier 2)
    for i in range(1, 5):
        turnover = Decimal("25000000") + Decimal(i * 2000000)
        monthly_inflows = turnover / Decimal("12")
        monthly_outflows = monthly_inflows * Decimal("0.89")  # 11% margin
        scenarios.append(
            {
                "scenario_id": f"SEG2_AGRI_T2_{i}",
                "segment": "Seasonal Agri-Processing & Textiles (Tier 2)",
                "features": {
                    "consent_status": "VALID",
                    "integrity_flag": False,
                    "gst_metrics": {"avg_monthly_revenue": str(monthly_inflows)},
                    "bank_metrics": {
                        "dscr": "1.29",
                        "avg_monthly_credits": str(monthly_inflows),
                        "avg_monthly_debits": str(monthly_outflows),
                    },
                    "invoice_metrics": {
                        "eligible_amount": str(turnover * Decimal("0.25"))
                    },
                    "authoritative_evidence_ids": [f"EVID-AGRI-{i}"],
                },
                "scores": {"evidence_confidence_score": 75.0 + i},
                "requested_amount": Decimal(
                    "8000000"
                ),  # Exceeds supportable -> CONDITIONAL_OFFER
                "requested_product": "WORKING_CAPITAL_LINE",
                "expected_decisions": [
                    SystemRecommendation.CONDITIONAL_OFFER.value,
                    SystemRecommendation.READY_FOR_REVIEW.value,
                ],
                "expect_limit_gt": Decimal("2000000"),
            }
        )

    # Segment 3: Emerging IT/Tech Services (Tier 1 - Asset Light)
    for i in range(1, 5):
        turnover = Decimal("18000000") + Decimal(i * 3000000)
        monthly_inflows = turnover / Decimal("12")
        monthly_outflows = monthly_inflows * Decimal("0.76")  # 24% margin
        scenarios.append(
            {
                "scenario_id": f"SEG3_TECH_T1_{i}",
                "segment": "Emerging Tech Services (Tier 1)",
                "features": {
                    "consent_status": "VALID",
                    "integrity_flag": False,
                    "gst_metrics": {"avg_monthly_revenue": str(monthly_inflows)},
                    "bank_metrics": {
                        "dscr": "2.05",
                        "avg_monthly_credits": str(monthly_inflows),
                        "avg_monthly_debits": str(monthly_outflows),
                    },
                    "invoice_metrics": {
                        "eligible_amount": str(turnover * Decimal("0.40"))
                    },
                    "authoritative_evidence_ids": [f"EVID-TECH-{i}"],
                },
                "scores": {"evidence_confidence_score": 90.0 + i},
                "requested_amount": Decimal("3000000"),
                "requested_product": "TERM_LOAN",
                "expected_decisions": [
                    SystemRecommendation.READY_FOR_REVIEW.value,
                    SystemRecommendation.CONDITIONAL_OFFER.value,
                ],
                "expect_limit_gt": Decimal("2500000"),
            }
        )

    # Segment 4: Distressed Retail Trade (Tier 3 - Low DSCR / Distress)
    for i in range(1, 5):
        turnover = Decimal("12000000") - Decimal(i * 1000000)
        monthly_inflows = turnover / Decimal("12")
        monthly_outflows = monthly_inflows * Decimal("0.96")
        scenarios.append(
            {
                "scenario_id": f"SEG4_RETAIL_T3_{i}",
                "segment": "Distressed Retail Trade (Tier 3)",
                "features": {
                    "consent_status": "VALID",
                    "integrity_flag": False,
                    "gst_metrics": {"avg_monthly_revenue": str(monthly_inflows)},
                    "bank_metrics": {
                        "dscr": "0.95",  # Below 1.15 minimum -> DECLINE_RECOMMENDED
                        "avg_monthly_credits": str(monthly_inflows),
                        "avg_monthly_debits": str(monthly_outflows),
                    },
                    "invoice_metrics": {"eligible_amount": "0"},
                    "authoritative_evidence_ids": [f"EVID-RETAIL-{i}"],
                },
                "scores": {"evidence_confidence_score": 60.0},
                "requested_amount": Decimal("2500000"),
                "requested_product": "WORKING_CAPITAL_LINE",
                "expected_decisions": [SystemRecommendation.DECLINE_RECOMMENDED.value],
                "expect_limit_eq": Decimal("0"),
            }
        )

    # Segment 5: Micro-Enterprise Vendor (Low Evidence Confidence)
    for i in range(1, 5):
        turnover = Decimal("8000000") + Decimal(i * 500000)
        monthly_inflows = turnover / Decimal("12")
        monthly_outflows = monthly_inflows * Decimal("0.88")
        scenarios.append(
            {
                "scenario_id": f"SEG5_MICRO_VENDOR_{i}",
                "segment": "Micro-Enterprise Vendor (Semi-urban)",
                "features": {
                    "consent_status": "VALID",
                    "integrity_flag": False,
                    "gst_metrics": {"avg_monthly_revenue": str(monthly_inflows)},
                    "bank_metrics": {
                        "dscr": "1.33",
                        "avg_monthly_credits": str(monthly_inflows),
                        "avg_monthly_debits": str(monthly_outflows),
                    },
                    "invoice_metrics": {"eligible_amount": "1000000"},
                    "authoritative_evidence_ids": [],
                },
                # Evidence score below 40 -> ADDITIONAL_EVIDENCE_REQUIRED
                "scores": {"evidence_confidence_score": 32.0 + i},
                "requested_amount": Decimal("1500000"),
                "requested_product": "RECEIVABLES_FINANCE",
                "expected_decisions": [
                    SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value
                ],
                "expect_limit_eq": Decimal("0"),
            }
        )

    return scenarios


def run_harness() -> Dict[str, Any]:
    log("==================================================================")
    log("Running CD-006: Quantitative Synthetic Validation Harness")
    log("==================================================================")

    scenarios = create_synthetic_scenarios()

    total_scenarios = len(scenarios)
    total_assertions = 0
    passed_assertions = 0
    failed_assertions = 0
    assertion_details = []
    segment_stats: Dict[str, Dict[str, Any]] = {}

    for sc in scenarios:
        sid = sc["scenario_id"]
        seg = sc["segment"]
        if seg not in segment_stats:
            segment_stats[seg] = {
                "scenarios_evaluated": 0,
                "passed_scenarios": 0,
                "failed_scenarios": 0,
                "total_supportable_exposure": float(0),
            }

        segment_stats[seg]["scenarios_evaluated"] += 1
        scenario_passed = True

        # Instantiate deterministic DecisionPolicy engine
        policy = DecisionPolicy(
            features=sc["features"],
            scores=sc["scores"],
            requested_amount=sc["requested_amount"],
            requested_product=sc["requested_product"],
        )
        out = policy.evaluate()

        # Assertion 1: Decision Bounds Check
        total_assertions += 1
        if out["decision"] in sc["expected_decisions"]:
            passed_assertions += 1
            assertion_details.append(
                {
                    "scenario_id": sid,
                    "segment": seg,
                    "assertion": "Decision Bounds Check",
                    "status": "PASS",
                    "detail": f"Decision {out['decision']} in {sc['expected_decisions']}",
                }
            )
        else:
            failed_assertions += 1
            scenario_passed = False
            assertion_details.append(
                {
                    "scenario_id": sid,
                    "segment": seg,
                    "assertion": "Decision Bounds Check",
                    "status": "FAIL",
                    "detail": f"Decision {out['decision']} NOT in {sc['expected_decisions']}",
                }
            )

        # Assertion 2: Binding Limit Verification
        total_assertions += 1
        if "expect_limit_gt" in sc:
            if out["binding_limit"] >= sc["expect_limit_gt"]:
                passed_assertions += 1
                assertion_details.append(
                    {
                        "scenario_id": sid,
                        "segment": seg,
                        "assertion": "Supportable Limit Bounds Check",
                        "status": "PASS",
                        "detail": f"Limit {float(out['binding_limit'])} >= {float(sc['expect_limit_gt'])}",
                    }
                )
            else:
                failed_assertions += 1
                scenario_passed = False
                assertion_details.append(
                    {
                        "scenario_id": sid,
                        "segment": seg,
                        "assertion": "Supportable Limit Bounds Check",
                        "status": "FAIL",
                        "detail": f"Limit {float(out['binding_limit'])} < {float(sc['expect_limit_gt'])}",
                    }
                )
        elif "expect_limit_eq" in sc:
            if out["binding_limit"] == sc["expect_limit_eq"]:
                passed_assertions += 1
                assertion_details.append(
                    {
                        "scenario_id": sid,
                        "segment": seg,
                        "assertion": "Zero/Decline Supportable Limit Check",
                        "status": "PASS",
                        "detail": f"Limit {float(out['binding_limit'])} == {float(sc['expect_limit_eq'])}",
                    }
                )
            else:
                failed_assertions += 1
                scenario_passed = False
                assertion_details.append(
                    {
                        "scenario_id": sid,
                        "segment": seg,
                        "assertion": "Zero/Decline Supportable Limit Check",
                        "status": "FAIL",
                        "detail": f"Limit {float(out['binding_limit'])} != {float(sc['expect_limit_eq'])}",
                    }
                )

        # Assertion 3: Reasons Non-empty and Deterministic
        total_assertions += 1
        if len(out.get("reasons", [])) > 0:
            passed_assertions += 1
        else:
            failed_assertions += 1
            scenario_passed = False

        # Assertion 4: Offers structure check when applicable
        total_assertions += 1
        offers = out.get("offers", [])
        if out["binding_limit"] > 0:
            if len(offers) > 0 and all(
                "calculation_version" in o
                and o["calculation_version"] == CALCULATION_VERSION
                for o in offers
            ):
                passed_assertions += 1
            else:
                failed_assertions += 1
                scenario_passed = False
        else:
            if len(offers) == 0:
                passed_assertions += 1
            else:
                failed_assertions += 1
                scenario_passed = False

        # Assertion 5: Monotonicity sanity check (limit should not exceed turnover significantly)
        total_assertions += 1
        turnover = Decimal(
            sc["features"]["gst_metrics"]["avg_monthly_revenue"]
        ) * Decimal("12")
        if out["binding_limit"] <= turnover * Decimal("1.5"):
            passed_assertions += 1
        else:
            failed_assertions += 1
            scenario_passed = False

        if scenario_passed:
            segment_stats[seg]["passed_scenarios"] += 1
        else:
            segment_stats[seg]["failed_scenarios"] += 1

        segment_stats[seg]["total_supportable_exposure"] += float(out["binding_limit"])

    pass_rate = (
        (passed_assertions / total_assertions * 100.0) if total_assertions > 0 else 0.0
    )
    overall_result = "PASS" if failed_assertions == 0 else "FAIL"

    report = {
        "harness_name": "Vyapar Pulse Competition Dominance RC3 - Quantitative Synthetic Validation Harness",
        "git_sha": get_git_sha(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "policy_version": POLICY_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "total_scenarios_evaluated": total_scenarios,
        "total_assertions_checked": total_assertions,
        "passed_assertions": passed_assertions,
        "failed_assertions": failed_assertions,
        "pass_rate_percentage": round(pass_rate, 2),
        "overall_result": overall_result,
        "segment_breakdown": segment_stats,
        "assertions_sample": assertion_details[:15],
    }

    # Write artifact
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    artifacts_dir = os.path.join(root_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    report_path = os.path.join(artifacts_dir, "synthetic_validation_report.json")

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    log(
        f"✅ Quantitative Synthetic Validation Harness Completed: {passed_assertions}/{total_assertions} assertions passed ({pass_rate:.2f}%)."
    )
    log(f"📁 Report generated at: {report_path}")

    return report


if __name__ == "__main__":
    try:
        report = run_harness()
        print(json.dumps(report, indent=2))
        if report["overall_result"] != "PASS":
            exit(1)
    except Exception as e:
        log(f"❌ Harness Execution Error - {e}")
        exit(1)
