from typing import Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from app.domain.financial.obligations import (
    ASSESSABLE_OBLIGATION_STATES,
    VERIFIED_ZERO_DEBT,
)


class ScoringEngine:
    """
    Computes deterministic scores based on derived features.
    Strictly bounded [0, 100].
    Returns exact Decimal values.
    """

    def __init__(self, features: Dict[str, Any]):
        self.features = features

    def compute_all_scores(self) -> Dict[str, Any]:
        evidence_score = self._compute_evidence_confidence()
        resilience_score = self._compute_resilience()
        fhi_data = self.compute_fhi_and_credit_score()

        return {
            "financial_health_score": fhi_data["financial_health_index"],
            "evidence_confidence_score": evidence_score.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "resilience_score": resilience_score.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "financial_health_index": fhi_data["financial_health_index"],
            "fhi_breakdown": fhi_data["fhi_breakdown"],
            "vyapar_credit_health_score": fhi_data["vyapar_credit_health_score"],
            "credit_health_disclaimer": fhi_data["credit_health_disclaimer"],
            "credit_score_disclaimer": fhi_data["credit_score_disclaimer"],
            "assessment_certainty": fhi_data["assessment_certainty"],
            "score_range": fhi_data["score_range"],
            "missing_material_evidence": fhi_data["missing_material_evidence"],
            "scoring_version": fhi_data["scoring_version"],
        }

    def compute_fhi_and_credit_score(self) -> Dict[str, Any]:
        """
        Computes an evidence-conditioned Financial Health Index (FHI).
        Missing material evidence abstains instead of awarding imputed positive points.
        """

        def get_dec(val: Any) -> Optional[Decimal]:
            if val is None or str(val).upper() in {"UNKNOWN", "", "NONE"}:
                return None
            try:
                return Decimal(str(val))
            except Exception:
                return None

        def q2(val: Decimal) -> Decimal:
            return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        def pillar(
            key: str,
            score: Optional[Decimal],
            weight: Decimal,
            status: str,
            observed: Dict[str, Any],
            missing: list[str],
            positive: list[str],
            adverse: list[str],
        ) -> Tuple[str, Dict[str, Any]]:
            max_score = Decimal("100")
            bounded = (
                None if score is None else min(max(score, Decimal("0")), max_score)
            )
            contribution = (
                None if bounded is None else q2((bounded / max_score) * weight)
            )
            evidence_ids = self.features.get("authoritative_evidence_ids", [])
            return key, {
                "score": float(q2(bounded)) if bounded is not None else None,
                "maximum_score": 100.0,
                "max_score": 100.0,
                "weight": float(weight),
                "weight_pct": float(weight),
                "contribution": float(contribution)
                if contribution is not None
                else None,
                "status": status,
                "observed_inputs": observed,
                "missing_inputs": missing,
                "evidence_ids": evidence_ids if isinstance(evidence_ids, list) else [],
                "positive_reason_codes": positive,
                "adverse_reason_codes": adverse,
            }

        bank = self.features.get("bank_metrics", {})
        recon = self.features.get("reconciliation_metrics", {})
        wc_metrics = self.features.get("working_capital_metrics", {})

        inflows = get_dec(bank.get("operating_inflows_monthly"))
        outflows = get_dec(bank.get("operating_outflows_monthly"))
        revenue = get_dec(self.features.get("monthly_revenue_inr")) or get_dec(
            self.features.get("gst_metrics", {}).get("avg_monthly_revenue")
        )
        operating_cash = (
            None if inflows is None or outflows is None else inflows - outflows
        )
        current_dscr = get_dec(bank.get("dscr"))
        if current_dscr is None:
            current_dscr = get_dec(self.features.get("current_dscr"))
        post_loan_dscr = get_dec(self.features.get("post_loan_dscr"))
        existing_ds = get_dec(
            self.features.get("verified_existing_debt_service_monthly")
        )
        if existing_ds is None:
            existing_ds = get_dec(bank.get("verified_debt_service_monthly"))
        obligation_state = self.features.get("obligation_verification_state")
        summary = bank.get("transaction_categorization_summary", {})
        unresolved_material = bool(summary.get("has_material_unresolved_activity"))

        missing_core = []
        if self.features.get("consent_status", "VALID") != "VALID":
            missing_core.append("valid_consent")
        if inflows is None or outflows is None or inflows <= 0:
            missing_core.append("governed_operating_cash_flow")
        if unresolved_material:
            missing_core.append("acceptable_unresolved_transaction_materiality")
        if obligation_state not in ASSESSABLE_OBLIGATION_STATES:
            missing_core.append("verified_obligations_or_verified_zero_debt")
        if revenue is None or revenue <= 0:
            missing_core.append("sufficient_revenue_evidence")

        # Liquidity - operating buffer and current ratio/cash buffer where available.
        if inflows is not None and inflows > 0 and operating_cash is not None:
            margin = operating_cash / inflows
            liquidity_score = (
                Decimal("100")
                if margin >= Decimal("0.20")
                else Decimal("80")
                if margin >= Decimal("0.12")
                else Decimal("60")
                if margin >= Decimal("0.05")
                else Decimal("30")
                if margin > 0
                else Decimal("0")
            )
            liquidity_status = "VERIFIED"
            liquidity_missing = []
        else:
            liquidity_score, liquidity_status, liquidity_missing = (
                None,
                "MISSING_DATA",
                ["operating_inflows_monthly", "operating_outflows_monthly"],
            )

        # Cash-flow capacity - only DSCR/cash from canonical capacity inputs.
        if (
            operating_cash is not None
            and existing_ds is not None
            and obligation_state in ASSESSABLE_OBLIGATION_STATES
        ):
            dscr_for_score = post_loan_dscr or current_dscr
            if (
                dscr_for_score is None
                and existing_ds == 0
                and obligation_state == VERIFIED_ZERO_DEBT
            ):
                dscr_for_score = Decimal("2.00")
            cashflow_score = (
                Decimal("100")
                if dscr_for_score >= Decimal("1.75")
                else Decimal("80")
                if dscr_for_score >= Decimal("1.40")
                else Decimal("60")
                if dscr_for_score >= Decimal("1.15")
                else Decimal("30")
                if dscr_for_score >= Decimal("1.00")
                else Decimal("0")
            )
            cashflow_status = "VERIFIED"
            cashflow_missing = []
        else:
            cashflow_score, cashflow_status, cashflow_missing = (
                None,
                "MISSING_DATA",
                ["canonical_capacity_dscr", "verified_obligations"],
            )

        # Revenue stability and momentum - real revenue series metrics only.
        gst = self.features.get("gst_metrics", {})
        months = int(gst.get("months_filed", 0) or 0)
        cv = get_dec(gst.get("revenue_cv"))
        trend = gst.get("trend")
        if months >= 6 and cv is not None:
            base = (
                Decimal("100")
                if cv <= Decimal("0.10")
                else Decimal("80")
                if cv <= Decimal("0.20")
                else Decimal("55")
                if cv <= Decimal("0.35")
                else Decimal("25")
            )
            if trend == "GROWING":
                base = min(Decimal("100"), base + Decimal("10"))
            elif trend == "DECLINING":
                base = max(Decimal("0"), base - Decimal("20"))
            revenue_score, revenue_status, revenue_missing = base, "VERIFIED", []
        else:
            revenue_score, revenue_status, revenue_missing = (
                None,
                "MISSING_DATA",
                ["six_month_revenue_series", "revenue_volatility"],
            )

        # Repayment burden and discipline - unknown obligations stay unknown.
        if obligation_state in ASSESSABLE_OBLIGATION_STATES and existing_ds is not None:
            burden = (
                Decimal("0")
                if operating_cash in (None, Decimal("0"))
                else existing_ds / max(operating_cash, Decimal("1"))
            )
            repay_score = (
                Decimal("100")
                if existing_ds == 0
                else Decimal("90")
                if burden <= Decimal("0.25")
                else Decimal("70")
                if burden <= Decimal("0.45")
                else Decimal("40")
                if burden <= Decimal("0.70")
                else Decimal("0")
            )
            repay_status, repay_missing = "VERIFIED", []
        else:
            repay_score, repay_status, repay_missing = (
                None,
                "MISSING_DATA",
                ["verified_existing_debt_service_monthly"],
            )

        # Compliance and formalisation - no reconciliation evidence means no points.
        ratio = get_dec(recon.get("gst_bank_ratio"))
        if ratio is not None and ratio > 0:
            compliance_score = (
                Decimal("100")
                if Decimal("0.95") <= ratio <= Decimal("1.05")
                else Decimal("80")
                if Decimal("0.90") <= ratio <= Decimal("1.10")
                else Decimal("55")
                if Decimal("0.80") <= ratio <= Decimal("1.20")
                else Decimal("20")
            )
            compliance_status, compliance_missing = "VERIFIED", []
        else:
            compliance_score, compliance_status, compliance_missing = (
                None,
                "MISSING_DATA",
                ["gst_bank_reconciliation"],
            )

        # Concentration and resilience - missing concentration/cycle abstains this pillar.
        inv = self.features.get("receivable_metrics") or self.features.get(
            "invoice_metrics", {}
        )
        concentration = get_dec(inv.get("top_buyer_concentration"))
        cycle = get_dec(wc_metrics.get("operating_cycle_days")) or get_dec(
            self.features.get("operating_cycle_days")
        )
        if concentration is not None and cycle is not None:
            conc_component = (
                Decimal("100")
                if concentration <= Decimal("0.25")
                else Decimal("75")
                if concentration <= Decimal("0.40")
                else Decimal("45")
                if concentration <= Decimal("0.60")
                else Decimal("10")
            )
            cycle_component = (
                Decimal("100")
                if cycle <= Decimal("45")
                else Decimal("75")
                if cycle <= Decimal("75")
                else Decimal("45")
                if cycle <= Decimal("105")
                else Decimal("10")
            )
            resilience_score = (conc_component + cycle_component) / Decimal("2")
            resilience_status, resilience_missing = "VERIFIED", []
        else:
            resilience_score, resilience_status, resilience_missing = (
                None,
                "MISSING_DATA",
                ["top_payer_concentration", "operating_cycle_days"],
            )

        pillar_items = dict(
            [
                pillar(
                    "liquidity",
                    liquidity_score,
                    Decimal("20"),
                    liquidity_status,
                    {
                        "operating_inflows_monthly": str(inflows),
                        "operating_outflows_monthly": str(outflows),
                    },
                    liquidity_missing,
                    ["OPERATING_BUFFER_VERIFIED"]
                    if liquidity_score is not None and liquidity_score >= 60
                    else [],
                    ["WEAK_OPERATING_BUFFER"] if liquidity_score == 0 else [],
                ),
                pillar(
                    "cash_flow_capacity",
                    cashflow_score,
                    Decimal("25"),
                    cashflow_status,
                    {
                        "operating_cash_available": str(operating_cash),
                        "current_dscr": str(current_dscr),
                        "post_loan_dscr": str(post_loan_dscr),
                    },
                    cashflow_missing,
                    ["DSCR_CAPACITY_VERIFIED"]
                    if cashflow_score is not None and cashflow_score >= 60
                    else [],
                    ["LOW_DSCR"] if cashflow_score == 0 else [],
                ),
                pillar(
                    "revenue_stability_momentum",
                    revenue_score,
                    Decimal("15"),
                    revenue_status,
                    {"months_filed": months, "revenue_cv": str(cv), "trend": trend},
                    revenue_missing,
                    ["REVENUE_SERIES_STABLE"]
                    if revenue_score is not None and revenue_score >= 60
                    else [],
                    ["REVENUE_VOLATILITY_OR_DECLINE"] if revenue_score == 0 else [],
                ),
                pillar(
                    "repayment_burden_discipline",
                    repay_score,
                    Decimal("20"),
                    repay_status,
                    {"verified_existing_debt_service_monthly": str(existing_ds)},
                    repay_missing,
                    ["OBLIGATIONS_VERIFIED"] if repay_score is not None else [],
                    ["HIGH_REPAYMENT_BURDEN"] if repay_score == 0 else [],
                ),
                pillar(
                    "compliance_formalisation",
                    compliance_score,
                    Decimal("10"),
                    compliance_status,
                    {"gst_bank_ratio": str(ratio)},
                    compliance_missing,
                    ["GST_BANK_RECONCILED"]
                    if compliance_score is not None and compliance_score >= 60
                    else [],
                    ["GST_BANK_RECONCILIATION_WEAK"] if compliance_score == 0 else [],
                ),
                pillar(
                    "concentration_resilience",
                    resilience_score,
                    Decimal("10"),
                    resilience_status,
                    {
                        "top_buyer_concentration": str(concentration),
                        "operating_cycle_days": str(cycle),
                    },
                    resilience_missing,
                    ["DIVERSIFIED_AND_CYCLE_VERIFIED"]
                    if resilience_score is not None and resilience_score >= 60
                    else [],
                    ["CONCENTRATION_OR_CYCLE_WEAK"] if resilience_score == 0 else [],
                ),
            ]
        )

        material_missing = missing_core + [
            missing
            for item in pillar_items.values()
            if item["status"] == "MISSING_DATA"
            for missing in item["missing_inputs"]
        ]

        assessable = not missing_core and all(
            pillar_items[key]["score"] is not None
            for key in (
                "liquidity",
                "cash_flow_capacity",
                "revenue_stability_momentum",
                "repayment_burden_discipline",
            )
        )

        if assessable:
            fhi_dec = q2(
                sum(
                    Decimal(str(item["contribution"]))
                    for item in pillar_items.values()
                    if item["contribution"] is not None
                )
            )
            vyapar_credit_health_score = int(
                min(
                    Decimal("900"),
                    max(Decimal("300"), Decimal("300") + Decimal("6") * fhi_dec),
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            missing_count = sum(
                1 for item in pillar_items.values() if item["status"] == "MISSING_DATA"
            )
            assessment_certainty = (
                "HIGH_CERTAINTY"
                if missing_count == 0
                else "MODERATE_CERTAINTY"
                if missing_count <= 1
                else "LIMITED_CERTAINTY"
            )
            band = {
                "HIGH_CERTAINTY": 15,
                "MODERATE_CERTAINTY": 30,
                "LIMITED_CERTAINTY": 50,
            }[assessment_certainty]
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
            "assessment_certainty": assessment_certainty,
            "score_range": score_range,
            "missing_material_evidence": sorted(set(material_missing)),
            "credit_health_disclaimer": disclaimer,
            "credit_score_disclaimer": disclaimer,
            "scoring_version": "3.0-EVIDENCE-CONDITIONED-FHI",
        }

    def _compute_financial_health(self) -> Decimal:
        """
        Base: 40
        + DSCR and operational surplus component (max 25)
        + GST Bank Reconciliation consistency (max 20)
        + Revenue Trend (max 15)
        Bounded [0.00, 100.00]
        """
        score = Decimal("40.0")

        # DSCR & Surplus component
        bank = self.features.get("bank_metrics", {})
        dscr_val = bank.get("dscr", "1.0")
        try:
            dscr = Decimal(str(dscr_val)) if dscr_val is not None else Decimal("1.0")
        except Exception:
            dscr = Decimal("1.0")

        if dscr >= Decimal("2.0"):
            score += Decimal("25.0")
        elif dscr >= Decimal("1.5"):
            score += Decimal("18.0")
        elif dscr >= Decimal("1.25"):
            score += Decimal("12.0")
        elif dscr >= Decimal("1.0"):
            score += Decimal("6.0")

        # Operational surplus check
        try:
            credits = Decimal(str(bank.get("avg_monthly_credits", "0")))
            debits = Decimal(str(bank.get("avg_monthly_debits", "0")))
            if credits > debits and credits > Decimal("0"):
                surplus_margin = (credits - debits) / credits
                if surplus_margin >= Decimal("0.15"):
                    score += Decimal("5.0")  # Bonus within cap
        except Exception:
            pass

        # GST Bank Reconciliation consistency
        recon = self.features.get("reconciliation_metrics", {})
        ratio_val = recon.get("gst_bank_ratio", "0")
        try:
            ratio = Decimal(str(ratio_val))
        except Exception:
            ratio = Decimal("0")

        if Decimal("0.9") <= ratio <= Decimal("1.1"):
            score += Decimal("20.0")
        elif Decimal("0.8") <= ratio <= Decimal("1.2"):
            score += Decimal("14.0")
        elif Decimal("0.7") <= ratio <= Decimal("1.3"):
            score += Decimal("7.0")

        # Revenue Trend
        gst = self.features.get("gst_metrics", {})
        trend = gst.get("trend", "UNKNOWN")
        if trend == "GROWING":
            score += Decimal("15.0")
        elif trend == "STABLE":
            score += Decimal("10.0")

        return min(max(score, Decimal("0.0")), Decimal("100.0"))

    def _compute_evidence_confidence(self) -> Decimal:
        """
        Based on number of data sources and months of history.
        Reduces confidence when settlement data is missing (UNKNOWN).
        """
        score = Decimal("0.0")

        gst = self.features.get("gst_metrics", {})
        months = int(gst.get("months_filed", 0))

        if months >= 18:
            score += Decimal("55.0")
        elif months >= 12:
            score += Decimal("38.0")
        elif months >= 6:
            score += Decimal("20.0")

        emp = self.features.get("employment_metrics", {})
        if int(emp.get("months_filed", 0)) > 6:
            score += Decimal("20.0")

        inv = self.features.get("receivable_metrics") or self.features.get(
            "invoice_metrics", {}
        )
        if int(inv.get("total_invoices", 0)) > 10:
            delay_val = str(inv.get("avg_payment_delay_days", ""))
            if delay_val == "UNKNOWN" or not delay_val:
                # Reduce points when settlement dates are unknown
                score += Decimal("10.0")
            else:
                score += Decimal("25.0")

        return min(max(score, Decimal("0.0")), Decimal("100.0"))

    def _compute_resilience(self) -> Decimal:
        """
        Penalized by buyer concentration and payment delays.
        Base 100, deduct for risks.
        """
        score = Decimal("100.0")

        inv = self.features.get("receivable_metrics") or self.features.get(
            "invoice_metrics", {}
        )
        try:
            concentration = Decimal(str(inv.get("top_buyer_concentration", "1.0")))
        except Exception:
            concentration = Decimal("1.0")

        if concentration > Decimal("0.6"):
            score -= Decimal("40.0")
        elif concentration > Decimal("0.4"):
            score -= Decimal("20.0")
        elif concentration > Decimal("0.2"):
            score -= Decimal("10.0")

        delay_val = str(inv.get("avg_payment_delay_days", "0"))
        if delay_val == "UNKNOWN" or not delay_val:
            # If unknown delay, apply a moderate precautionary deduction
            score -= Decimal("15.0")
        else:
            try:
                delay = int(float(delay_val))
                if delay > 60:
                    score -= Decimal("30.0")
                elif delay > 30:
                    score -= Decimal("15.0")
            except Exception:
                score -= Decimal("15.0")

        gst = self.features.get("gst_metrics", {})
        try:
            cv = Decimal(str(gst.get("revenue_cv", "1.0")))
        except Exception:
            cv = Decimal("1.0")

        if cv > Decimal("0.3"):
            score -= Decimal("20.0")
        elif cv > Decimal("0.15"):
            score -= Decimal("10.0")

        return min(max(score, Decimal("0.0")), Decimal("100.0"))
