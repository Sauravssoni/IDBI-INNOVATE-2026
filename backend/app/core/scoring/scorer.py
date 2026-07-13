from decimal import Decimal
from typing import Dict, Any

class ScoringEngine:
    def __init__(self, features: Dict[str, Any]):
        self.features = features

    def compute_all_scores(self) -> Dict[str, Any]:
        from app.domain.financial.engine import FinancialCapacityEngine
        
        # 1. Capacity Bridge: Delegate to authoritative engine instead of guessing
        cap = FinancialCapacityEngine.compute_capacity_from_features(self.features)
        
        inflows = cap["observed_operating_inflows_monthly"]
        operating_cash = cap["operating_cash_available_for_debt_service_monthly"]
        existing_ds = cap["verified_existing_debt_service_monthly"]
        obligation_state = cap["obligation_verification_state"]
        cash_flow_status = cap["cash_flow_status"]
        
        evd = cap["calculation_evidence_ids"]
        inflow_evd = evd.get("inflows", [])
        outflow_evd = evd.get("outflows", [])
        obligation_evd = evd.get("obligations", [])
        gst_metrics = self.features.get("gst_metrics", {})
        gst_evd = gst_metrics.get("gst_evidence_ids", [])
        
        ASSESSABLE_OBLIGATION_STATES = ["VERIFIED_OBLIGATIONS", "VERIFIED_ZERO_DEBT"]
        
        missing_core = []
        if cash_flow_status == "INSUFFICIENT_CASH_FLOW_DATA":
            missing_core.append("operating_cash_flow")
            
        ledger = []
        running = Decimal("300.0")
        
        # 1. Base
        ledger.append({
            "rule_id": "SC-001",
            "pillar": "Base Score",
            "input_name": "Base",
            "input_value": "N/A",
            "threshold_or_band": "Default",
            "raw_points": 300.0,
            "weighted_points": 300.0,
            "direction": "NEUTRAL",
            "reason_code": "BASE_300",
            "technical_explanation": "Starting base score.",
            "applicant_explanation_en": "Starting base score.",
            "applicant_explanation_hi": "आधार स्कोर।",
            "evidence_ids": [],
            "running_score": 300.0
        })
        
        # 2. Liquidity (Max 120 pts)
        if inflows > 0 and cash_flow_status == "SUFFICIENT_CASH_FLOW_DATA":
            margin = operating_cash / inflows
            liq_pts = Decimal("120") if margin >= Decimal("0.2") else Decimal("80") if margin >= Decimal("0.1") else Decimal("40") if margin > 0 else Decimal("0")
            running += liq_pts
            ledger.append({
                "rule_id": "SC-002", "pillar": "Liquidity", "input_name": "Operating Margin",
                "input_value": f"{margin*100:.1f}%", "threshold_or_band": ">10%",
                "raw_points": float(liq_pts), "weighted_points": float(liq_pts),
                "direction": "POSITIVE" if liq_pts > 40 else "NEGATIVE",
                "reason_code": "LIQ_MARGIN", "technical_explanation": "Operating margin points",
                "applicant_explanation_en": "Healthy cash buffer.", "applicant_explanation_hi": "स्वस्थ नकदी बफर।",
                "evidence_ids": inflow_evd + outflow_evd, "running_score": float(running)
            })
            liq_status, liq_missing = "VERIFIED", []
        else:
            liq_pts, liq_status, liq_missing = None, "MISSING_DATA", ["operating_inflows_monthly"]
            
        # 3. Cash Flow Capacity (Max 150 pts)
        existing_dscr = None
        if obligation_state in ASSESSABLE_OBLIGATION_STATES and cash_flow_status == "SUFFICIENT_CASH_FLOW_DATA" and operating_cash > 0:
            
            existing_dscr = operating_cash / max(Decimal("1"), existing_ds)
            cf_pts = Decimal("150") if existing_dscr >= Decimal("2.0") else Decimal("100") if existing_dscr >= Decimal("1.5") else Decimal("50") if existing_dscr >= Decimal("1.1") else Decimal("0")
            running += cf_pts
            ledger.append({
                "rule_id": "SC-003", "pillar": "Cash Flow Capacity", "input_name": "DSCR",
                "input_value": f"{existing_dscr:.2f}x", "threshold_or_band": ">1.5x",
                "raw_points": float(cf_pts), "weighted_points": float(cf_pts),
                "direction": "POSITIVE" if cf_pts > 50 else "NEGATIVE",
                "reason_code": "CF_DSCR", "technical_explanation": "DSCR points",
                "applicant_explanation_en": "Strong debt coverage.", "applicant_explanation_hi": "मजबूत ऋण कवरेज।",
                "evidence_ids": inflow_evd + outflow_evd + obligation_evd, "running_score": float(running)
            })
            cf_status, cf_missing = "VERIFIED", []
        else:
            cf_pts, cf_status, cf_missing = None, "MISSING_DATA", ["verified_existing_debt_service_monthly"]

        # 4. Revenue Stability (Max 90 pts)
        months = int(gst_metrics.get("months_filed", 0))
        cv_val = gst_metrics.get("revenue_cv", "UNKNOWN")
        if months >= 6 and cv_val != "UNKNOWN":
            cv = Decimal(str(cv_val))
            rev_pts = Decimal("90") if cv <= Decimal("0.15") else Decimal("60") if cv <= Decimal("0.30") else Decimal("20")
            running += rev_pts
            ledger.append({
                "rule_id": "SC-004", "pillar": "Revenue Stability", "input_name": "Revenue CV",
                "input_value": f"{cv*100:.1f}%", "threshold_or_band": "<30%",
                "raw_points": float(rev_pts), "weighted_points": float(rev_pts),
                "direction": "POSITIVE" if rev_pts > 20 else "NEGATIVE",
                "reason_code": "REV_STAB", "technical_explanation": "Revenue CV points",
                "applicant_explanation_en": "Stable revenue.", "applicant_explanation_hi": "स्थिर राजस्व।",
                "evidence_ids": gst_evd, "running_score": float(running)
            })
            rev_status, rev_missing = "VERIFIED", []
        else:
            rev_pts, rev_status, rev_missing = None, "MISSING_DATA", ["six_month_revenue_series"]

        # 5. Repayment Burden (Max 120 pts)
        if obligation_state in ASSESSABLE_OBLIGATION_STATES and cash_flow_status == "SUFFICIENT_CASH_FLOW_DATA" and operating_cash > 0:
            burden = existing_ds / operating_cash
            rep_pts = Decimal("120") if burden <= Decimal("0.25") else Decimal("80") if burden <= Decimal("0.45") else Decimal("30") if burden <= Decimal("0.70") else Decimal("0")
            running += rep_pts
            ledger.append({
                "rule_id": "SC-005", "pillar": "Repayment Burden", "input_name": "Existing Burden",
                "input_value": f"{burden*100:.1f}%", "threshold_or_band": "<45%",
                "raw_points": float(rep_pts), "weighted_points": float(rep_pts),
                "direction": "POSITIVE" if rep_pts > 30 else "NEGATIVE",
                "reason_code": "REP_BURD", "technical_explanation": "Repayment burden points",
                "applicant_explanation_en": "Low existing debt.", "applicant_explanation_hi": "कम मौजूदा कर्ज।",
                "evidence_ids": obligation_evd + inflow_evd, "running_score": float(running)
            })
            rep_status, rep_missing = "VERIFIED", []
        else:
            rep_pts, rep_status, rep_missing = None, "MISSING_DATA", ["verified_existing_debt_service_monthly"]

        # 6. Compliance (Max 60 pts)
        recon = self.features.get("reconciliation_metrics", {})
        ratio_val = recon.get("gst_bank_ratio", "UNKNOWN")
        if ratio_val != "UNKNOWN":
            ratio = Decimal(str(ratio_val))
            comp_pts = Decimal("60") if Decimal("0.90") <= ratio <= Decimal("1.10") else Decimal("30") if Decimal("0.80") <= ratio <= Decimal("1.20") else Decimal("0")
            running += comp_pts
            ledger.append({
                "rule_id": "SC-006", "pillar": "Compliance", "input_name": "GST/Bank Ratio",
                "input_value": f"{ratio:.2f}", "threshold_or_band": "0.9-1.1",
                "raw_points": float(comp_pts), "weighted_points": float(comp_pts),
                "direction": "POSITIVE" if comp_pts > 0 else "NEGATIVE",
                "reason_code": "COMP_RECON", "technical_explanation": "GST vs Bank reconciliation",
                "applicant_explanation_en": "Strong compliance.", "applicant_explanation_hi": "मजबूत अनुपालन।",
                "evidence_ids": gst_evd + inflow_evd, "running_score": float(running)
            })
            comp_status, comp_missing = "VERIFIED", []
        else:
            comp_pts, comp_status, comp_missing = None, "MISSING_DATA", ["gst_bank_reconciliation"]
            
        # 7. Resilience (Max 60 pts)
        inv = self.features.get("receivable_metrics") or self.features.get("invoice_metrics", {})
        conc_val = inv.get("top_buyer_concentration", "UNKNOWN")
        if conc_val != "UNKNOWN":
            conc = Decimal(str(conc_val))
            res_pts = Decimal("60") if conc <= Decimal("0.25") else Decimal("30") if conc <= Decimal("0.40") else Decimal("0")
            running += res_pts
            ledger.append({
                "rule_id": "SC-007", "pillar": "Resilience", "input_name": "Buyer Concentration",
                "input_value": f"{conc*100:.1f}%", "threshold_or_band": "<25%",
                "raw_points": float(res_pts), "weighted_points": float(res_pts),
                "direction": "POSITIVE" if res_pts > 0 else "NEGATIVE",
                "reason_code": "RES_CONC", "technical_explanation": "Buyer concentration points",
                "applicant_explanation_en": "Diversified buyers.", "applicant_explanation_hi": "विविध खरीदार।",
                "evidence_ids": gst_evd, "running_score": float(running)
            })
            res_status, res_missing = "VERIFIED", []
        else:
            res_pts, res_status, res_missing = None, "MISSING_DATA", ["top_buyer_concentration"]

        assessable = not missing_core and all(p is not None for p in [liq_pts, cf_pts, rev_pts, rep_pts])
        
        def pillar(name, pts, max_pts, stat, miss):
            return {
                "name": name,
                "score": int(pts) if pts is not None else None,
                "contribution": int(pts) if pts is not None else None,
                "status": stat,
                "missing_inputs": miss,
                "positive_reason_codes": [],
                "adverse_reason_codes": [],
                "evidence_ids": []
            }
            
        pillar_items = {
            "liquidity": pillar("Liquidity", liq_pts, 120, liq_status, liq_missing),
            "cash_flow_capacity": pillar("Cash Flow Capacity", cf_pts, 150, cf_status, cf_missing),
            "revenue_stability_momentum": pillar("Revenue Stability", rev_pts, 90, rev_status, rev_missing),
            "repayment_burden_discipline": pillar("Repayment Burden", rep_pts, 120, rep_status, rep_missing),
            "compliance_formalisation": pillar("Compliance", comp_pts, 60, comp_status, comp_missing),
            "concentration_resilience": pillar("Concentration", res_pts, 60, res_status, res_missing)
        }

        if assessable:
            vyapar_credit_health_score = int(running)
            fhi_dec = Decimal(str(vyapar_credit_health_score - 300)) / Decimal("6")
            
            missing_count = sum(1 for item in pillar_items.values() if item["status"] == "MISSING_DATA")
            # Evidence widens the range
            band = 15 if missing_count == 0 else 30 if missing_count <= 1 else 50
            assessment_certainty = "HIGH_CERTAINTY" if missing_count == 0 else "MODERATE_CERTAINTY" if missing_count <= 1 else "LIMITED_CERTAINTY"
            
            score_range = {
                "lower": max(300, vyapar_credit_health_score - band),
                "upper": min(900, vyapar_credit_health_score + band),
                "basis": "evidence-conditioned assessment range; not a statistical confidence interval",
            }
        else:
            fhi_dec = None
            vyapar_credit_health_score = None
            assessment_certainty = "INSUFFICIENT_TO_ASSESS"
            score_range = None
            ledger = []

        disclaimer = (
            "Indicative MSME Credit Health Score — not a bureau score, probability of default or sanction decision. "
            "The score describes financial condition. Certainty describes how complete and reliable the evidence is. "
            "Integrity identifies contradictions or manipulation risks. Policy determines what may proceed. "
            "A human authority makes the final decision."
        )

        return {
            "financial_health_index": fhi_dec,
            "vyapar_credit_health_score": vyapar_credit_health_score,
            "fhi_breakdown": pillar_items,
            "score_contribution_ledger": ledger,
            "base_score": 300,
            "positive_contributions": sum(L["weighted_points"] for L in ledger if L["direction"] == "POSITIVE" and L["pillar"] != "Base Score"),
            "adverse_contributions": sum(L["weighted_points"] for L in ledger if L["direction"] == "NEGATIVE"),
            "final_financial_score": vyapar_credit_health_score,
            "assessment_certainty": assessment_certainty,
            "score_range": score_range,
            "credit_health_disclaimer": disclaimer,
            "credit_score_disclaimer": disclaimer,
            "scoring_version": "3.1-EVIDENCE-LINKED-FHI",
        }
