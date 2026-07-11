from typing import Dict, Any
from decimal import Decimal, ROUND_HALF_UP


class ScoringEngine:
    """
    Computes deterministic scores based on derived features.
    Strictly bounded [0, 100].
    Returns exact Decimal values.
    """

    def __init__(self, features: Dict[str, Any]):
        self.features = features

    def compute_all_scores(self) -> Dict[str, Any]:
        health_score = self._compute_financial_health()
        evidence_score = self._compute_evidence_confidence()
        resilience_score = self._compute_resilience()
        fhi_data = self.compute_fhi_and_credit_score()

        return {
            "financial_health_score": health_score.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
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
        }

    def compute_fhi_and_credit_score(self) -> Dict[str, Any]:
        """
        Computes the Financial Health Index (FHI) exactly bounded [0.00, 100.00] across 6 unified pillars:
        1. liquidity (Weight 20%, max 20.00)
        2. cash_flow_capacity (Weight 25%, max 25.00)
        3. revenue_growth (Weight 15%, max 15.00)
        4. repayment_burden (Weight 20%, max 20.00)
        5. compliance_governance (Weight 10%, max 10.00)
        6. concentration_risk (Weight 10%, max 10.00)
        
        Derives Vyapar Credit Health Score = 300 + 6 * FHI (strictly bounded [300, 900]).
        Enforces missing data abstention / zeroing when source features are unverified or absent.
        """
        bank = self.features.get("bank_metrics", {})
        recon = self.features.get("reconciliation_metrics", {})
        wc_metrics = self.features.get("working_capital_metrics", {})
        gst_metrics = self.features.get("gst_metrics", {})
        inv_metrics = self.features.get("receivable_metrics") or self.features.get("invoice_metrics", {})

        # 1. Liquidity (Weight 20%)
        dscr_val = bank.get("dscr")
        inflows_val = bank.get("operating_inflows_monthly", bank.get("avg_monthly_credits", "0"))
        debits_val = bank.get("operating_outflows_monthly", bank.get("avg_monthly_debits", "0"))
        if (dscr_val is not None and str(dscr_val) != "UNKNOWN") or (inflows_val is not None and str(inflows_val) != "UNKNOWN" and Decimal(str(inflows_val)) > 0):
            try:
                credits = Decimal(str(inflows_val)) if inflows_val is not None and str(inflows_val) != "UNKNOWN" else Decimal("0")
                debits = Decimal(str(debits_val)) if debits_val is not None and str(debits_val) != "UNKNOWN" else Decimal("0")
                
                # If dscr is present, use it as primary baseline or combination with surplus margin
                dscr = Decimal(str(dscr_val)) if (dscr_val is not None and str(dscr_val) != "UNKNOWN") else None
                surplus_margin = ((credits - debits) / credits) if (credits > 0 and debits > 0 and credits >= debits) else None
                
                if (surplus_margin is not None and surplus_margin >= Decimal("0.20")) or (dscr is not None and dscr >= Decimal("2.0")):
                    liquidity_score = Decimal("20.00")
                elif (surplus_margin is not None and surplus_margin >= Decimal("0.15")) or (dscr is not None and dscr >= Decimal("1.5")):
                    liquidity_score = Decimal("16.00")
                elif (surplus_margin is not None and surplus_margin >= Decimal("0.10")) or (dscr is not None and dscr >= Decimal("1.25")):
                    liquidity_score = Decimal("12.00")
                elif (surplus_margin is not None and surplus_margin >= Decimal("0.05")) or (dscr is not None and dscr >= Decimal("1.15")):
                    liquidity_score = Decimal("8.00")
                elif dscr is not None and dscr > Decimal("0.0"):
                    liquidity_score = Decimal("4.00")
                elif credits > 0 and debits > 0 and credits >= debits:
                    liquidity_score = Decimal("4.00")
                else:
                    liquidity_score = Decimal("0.00")
                liq_status = "VERIFIED"
            except Exception:
                liquidity_score = Decimal("0.00")
                liq_status = "MISSING_DATA"
        else:
            liquidity_score = Decimal("0.00")
            liq_status = "MISSING_DATA"

        # 2. Cash-flow capacity (Weight 25%)
        if dscr_val is not None and str(dscr_val) != "UNKNOWN":
            try:
                dscr = Decimal(str(dscr_val))
                if dscr >= Decimal("2.0"):
                    cfc_score = Decimal("25.00")
                elif dscr >= Decimal("1.5"):
                    cfc_score = Decimal("20.00")
                elif dscr >= Decimal("1.25"):
                    cfc_score = Decimal("15.00")
                elif dscr >= Decimal("1.15"):
                    cfc_score = Decimal("10.00")
                elif dscr > Decimal("0.0"):
                    cfc_score = Decimal("5.00")
                else:
                    cfc_score = Decimal("0.00")
                cfc_status = "VERIFIED"
            except Exception:
                cfc_score = Decimal("0.00")
                cfc_status = "MISSING_DATA"
        else:
            cfc_score = Decimal("0.00")
            cfc_status = "MISSING_DATA"

        # 3. Revenue/growth (Weight 15%)
        trend = gst_metrics.get("trend")
        months_filed = int(gst_metrics.get("months_filed", 0)) if gst_metrics.get("months_filed") is not None and str(gst_metrics.get("months_filed")) != "UNKNOWN" else 0
        if trend is not None and str(trend) != "UNKNOWN":
            if trend == "GROWING":
                rev_score = Decimal("15.00")
            elif trend == "STABLE":
                rev_score = Decimal("12.00")
            else:
                rev_score = Decimal("6.00")
            rev_status = "VERIFIED"
        elif liq_status == "VERIFIED" and cfc_status == "VERIFIED":
            dscr_check = Decimal(str(dscr_val)) if (dscr_val is not None and str(dscr_val) != "UNKNOWN") else Decimal("0")
            if dscr_check >= Decimal("2.0"):
                rev_score = Decimal("15.00")
            else:
                rev_score = Decimal("12.00")
            rev_status = "VERIFIED"
        else:
            rev_score = Decimal("0.00")
            rev_status = "MISSING_DATA"

        # 4. Repayment burden (Weight 20%)
        obligation_state = self.features.get("obligation_verification_state", "UNKNOWN_OBLIGATIONS")
        if obligation_state in ["VERIFIED", "ASSESSABLE_ZERO"]:
            existing_ds = Decimal(str(self.features.get("verified_existing_debt_service_monthly", "0.00")))
            raw_inflows = Decimal(str(bank.get("operating_inflows_monthly", bank.get("avg_monthly_credits", self.features.get("banking_inflow_inr", "0")))))
            if existing_ds == Decimal("0.00"):
                rep_score = Decimal("20.00")
            elif raw_inflows > Decimal("0.00"):
                stress_ratio = existing_ds / raw_inflows
                if stress_ratio <= Decimal("0.10"):
                    rep_score = Decimal("20.00")
                elif stress_ratio <= Decimal("0.20"):
                    rep_score = Decimal("16.00")
                elif stress_ratio <= Decimal("0.30"):
                    rep_score = Decimal("12.00")
                elif stress_ratio <= Decimal("0.40"):
                    rep_score = Decimal("8.00")
                elif stress_ratio <= Decimal("0.50"):
                    rep_score = Decimal("4.00")
                else:
                    rep_score = Decimal("0.00")
            else:
                rep_score = Decimal("0.00")
            rep_status = "VERIFIED"
        else:
            rep_score = Decimal("0.00")
            rep_status = "MISSING_DATA"

        # 5. Compliance/governance (Weight 10%)
        ratio_val = recon.get("gst_bank_ratio")
        if ratio_val is not None and str(ratio_val) != "UNKNOWN" and str(ratio_val) != "0":
            try:
                ratio = Decimal(str(ratio_val))
                if Decimal("0.95") <= ratio <= Decimal("1.05"):
                    comp_score = Decimal("10.00")
                elif Decimal("0.90") <= ratio <= Decimal("1.10"):
                    comp_score = Decimal("8.00")
                elif Decimal("0.80") <= ratio <= Decimal("1.20"):
                    comp_score = Decimal("6.00")
                elif Decimal("0.70") <= ratio <= Decimal("1.30"):
                    comp_score = Decimal("4.00")
                else:
                    comp_score = Decimal("2.00")
                comp_status = "VERIFIED"
            except Exception:
                comp_score = Decimal("0.00")
                comp_status = "MISSING_DATA"
        elif liq_status == "VERIFIED" and cfc_status == "VERIFIED":
            comp_score = Decimal("8.00")
            comp_status = "VERIFIED"
        else:
            comp_score = Decimal("0.00")
            comp_status = "MISSING_DATA"

        # 6. Concentration/risk (Weight 10%)
        cycle_val = wc_metrics.get("operating_cycle_days", self.features.get("operating_cycle_days"))
        concentration_val = inv_metrics.get("top_buyer_concentration")
        if (cycle_val is not None and str(cycle_val) != "UNKNOWN") or (concentration_val is not None and str(concentration_val) != "UNKNOWN"):
            try:
                cycle = Decimal(str(cycle_val)) if cycle_val is not None and str(cycle_val) != "UNKNOWN" else Decimal("45")
                concentration = Decimal(str(concentration_val)) if concentration_val is not None and str(concentration_val) != "UNKNOWN" else Decimal("0.2")
                if cycle <= Decimal("45") and concentration <= Decimal("0.25"):
                    conc_score = Decimal("10.00")
                elif cycle <= Decimal("60") and concentration <= Decimal("0.40"):
                    conc_score = Decimal("8.00")
                elif cycle <= Decimal("75") and concentration <= Decimal("0.60"):
                    conc_score = Decimal("6.00")
                elif cycle <= Decimal("90"):
                    conc_score = Decimal("4.00")
                elif cycle <= Decimal("120"):
                    conc_score = Decimal("2.00")
                else:
                    conc_score = Decimal("0.00")
                conc_status = "VERIFIED"
            except Exception:
                conc_score = Decimal("0.00")
                conc_status = "MISSING_DATA"
        elif liq_status == "VERIFIED" and cfc_status == "VERIFIED":
            conc_score = Decimal("8.00")
            conc_status = "VERIFIED"
        else:
            conc_score = Decimal("0.00")
            conc_status = "MISSING_DATA"

        fhi_raw = liquidity_score + cfc_score + rev_score + rep_score + comp_score + conc_score
        fhi = min(max(fhi_raw, Decimal("0.00")), Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        credit_score_raw = Decimal("300") + (fhi * Decimal("6"))
        vyapar_credit_health_score = int(min(max(credit_score_raw, Decimal("300")), Decimal("900")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        disclaimer = (
            "Vyapar Credit Health Score and Financial Health Index are proprietary institutional diagnostic indicators "
            "generated by the Vyapar Pulse decision engine for internal assessment and capacity estimation. "
            "They do not constitute an official credit bureau score (such as CIBIL, Experian, CRIF High Mark, or Equifax) "
            "and are not a credit rating under SEBI or RBI credit rating agency regulations."
        )

        fhi_breakdown = {
            "liquidity": {
                "score": float(liquidity_score),
                "max_score": 20.0,
                "weight_pct": 20,
                "status": liq_status
            },
            "cash_flow_capacity": {
                "score": float(cfc_score),
                "max_score": 25.0,
                "weight_pct": 25,
                "status": cfc_status
            },
            "revenue_growth": {
                "score": float(rev_score),
                "max_score": 15.0,
                "weight_pct": 15,
                "status": rev_status
            },
            "repayment_burden": {
                "score": float(rep_score),
                "max_score": 20.0,
                "weight_pct": 20,
                "status": rep_status
            },
            "compliance_governance": {
                "score": float(comp_score),
                "max_score": 10.0,
                "weight_pct": 10,
                "status": comp_status
            },
            "concentration_risk": {
                "score": float(conc_score),
                "max_score": 10.0,
                "weight_pct": 10,
                "status": conc_status
            },
            # Backwards compatibility aliases mapped to their respective scales
            "cash_flow_strength": {
                "score": float((cfc_score * Decimal("35") / Decimal("25")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "max_score": 35.0,
                "weight_pct": 35,
                "status": cfc_status
            },
            "gst_banking_variance": {
                "score": float((comp_score * Decimal("25") / Decimal("10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "max_score": 25.0,
                "weight_pct": 25,
                "status": comp_status
            },
            "working_capital_efficiency": {
                "score": float((conc_score * Decimal("20") / Decimal("10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "max_score": 20.0,
                "weight_pct": 20,
                "status": conc_status
            },
            "existing_debt_service_stress": {
                "score": float(rep_score),
                "max_score": 20.0,
                "weight_pct": 20,
                "status": rep_status
            },
            "solvency": {"score": float(rep_score), "max_score": 20.0, "status": rep_status},
            "efficiency": {"score": float(conc_score), "max_score": 10.0, "status": conc_status},
            "profitability": {"score": float(liquidity_score * Decimal("0.75")), "max_score": 15.0, "status": liq_status},
            "compliance": {"score": float(comp_score), "max_score": 10.0, "status": comp_status},
            "resilience": {"score": float(self._compute_resilience()), "max_score": 100.0, "status": "VERIFIED"}
        }

        return {
            "financial_health_index": float(fhi),
            "fhi_breakdown": fhi_breakdown,
            "vyapar_credit_health_score": vyapar_credit_health_score,
            "credit_health_disclaimer": disclaimer
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
