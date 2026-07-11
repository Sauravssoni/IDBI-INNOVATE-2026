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
        Computes the Financial Health Index (FHI) strictly based on 6 unified pillars.
        vyapar_credit_health_score exactly bounded between 0 and 900.
        financial_health_index perfectly mirrors it on a 0-100 scale (FHI = credit_health / 9).
        """
        def get_dec(val):
            if val is None or str(val) == "UNKNOWN" or str(val) == "": return None
            try: return Decimal(str(val))
            except: return None

        bank = self.features.get("bank_metrics", {})
        recon = self.features.get("reconciliation_metrics", {})
        wc_metrics = self.features.get("working_capital_metrics", {})
        
        # 1. Operating Resilience (Revenue - Expenses ratio)
        rev = get_dec(self.features.get("monthly_revenue_inr")) or Decimal("0")
        exp = get_dec(self.features.get("monthly_expenses_inr")) or Decimal("0")
        if rev > Decimal("0"):
            margin = (rev - exp) / rev
            if margin >= Decimal("0.20"): p1 = Decimal("150")
            elif margin >= Decimal("0.15"): p1 = Decimal("120")
            elif margin >= Decimal("0.10"): p1 = Decimal("90")
            elif margin >= Decimal("0.05"): p1 = Decimal("60")
            elif margin > Decimal("0.0"): p1 = Decimal("30")
            else: p1 = Decimal("0")
            p1_status = "VERIFIED"
        else:
            p1 = Decimal("0")
            p1_status = "MISSING_DATA"

        # 2. Cash Flow Health (Inflows vs Outflows matching)
        inflows_val = bank.get("operating_inflows_monthly") or bank.get("avg_monthly_credits") or self.features.get("banking_inflow_inr")
        outflows_val = bank.get("operating_outflows_monthly") or bank.get("avg_monthly_debits") or self.features.get("banking_outflow_inr")
        inflows = get_dec(inflows_val) or Decimal("0")
        outflows = get_dec(outflows_val) or Decimal("0")
        if inflows > Decimal("0"):
            cf_margin = (inflows - outflows) / inflows
            if cf_margin >= Decimal("0.15"): p2 = Decimal("150")
            elif cf_margin >= Decimal("0.10"): p2 = Decimal("120")
            elif cf_margin >= Decimal("0.05"): p2 = Decimal("90")
            elif cf_margin > Decimal("0.0"): p2 = Decimal("60")
            else: p2 = Decimal("0")
            p2_status = "VERIFIED"
        else:
            p2 = Decimal("0")
            p2_status = "MISSING_DATA"

        # 3. Margin Stability (Net profit margin)
        ebitda = get_dec(self.features.get("ebitda_monthly")) or Decimal("0")
        if rev > Decimal("0") and ebitda > Decimal("0"):
            npm = ebitda / rev
            if npm >= Decimal("0.15"): p3 = Decimal("150")
            elif npm >= Decimal("0.10"): p3 = Decimal("120")
            elif npm >= Decimal("0.05"): p3 = Decimal("90")
            else: p3 = Decimal("60")
            p3_status = "VERIFIED"
        elif p1_status == "VERIFIED":
            p3 = p1 * Decimal("0.8")
            p3_status = "IMPUTED"
        else:
            p3 = Decimal("0")
            p3_status = "MISSING_DATA"

        # 4. Working Capital Velocity (Quick ratio equivalent)
        cycle = get_dec(wc_metrics.get("operating_cycle_days")) or get_dec(self.features.get("operating_cycle_days"))
        if cycle is not None:
            if cycle <= Decimal("30"): p4 = Decimal("150")
            elif cycle <= Decimal("45"): p4 = Decimal("120")
            elif cycle <= Decimal("60"): p4 = Decimal("90")
            elif cycle <= Decimal("90"): p4 = Decimal("60")
            elif cycle <= Decimal("120"): p4 = Decimal("30")
            else: p4 = Decimal("0")
            p4_status = "VERIFIED"
        else:
            p4 = Decimal("60")
            p4_status = "IMPUTED"

        # 5. GST Compliance & Reporting
        ratio = get_dec(recon.get("gst_bank_ratio"))
        if ratio is not None and ratio != Decimal("0"):
            if Decimal("0.95") <= ratio <= Decimal("1.05"): p5 = Decimal("150")
            elif Decimal("0.90") <= ratio <= Decimal("1.10"): p5 = Decimal("120")
            elif Decimal("0.80") <= ratio <= Decimal("1.20"): p5 = Decimal("90")
            elif Decimal("0.70") <= ratio <= Decimal("1.30"): p5 = Decimal("60")
            else: p5 = Decimal("30")
            p5_status = "VERIFIED"
        else:
            p5 = Decimal("60")
            p5_status = "MISSING_DATA"

        # 6. Obligation Discipline (Debt service capability)
        dscr = get_dec(bank.get("dscr"))
        if dscr is not None:
            if dscr >= Decimal("2.0"): p6 = Decimal("150")
            elif dscr >= Decimal("1.75"): p6 = Decimal("120")
            elif dscr >= Decimal("1.5"): p6 = Decimal("90")
            elif dscr >= Decimal("1.25"): p6 = Decimal("60")
            elif dscr > Decimal("1.0"): p6 = Decimal("30")
            else: p6 = Decimal("0")
            p6_status = "VERIFIED"
        else:
            existing_ds = get_dec(self.features.get("verified_existing_debt_service_monthly")) or Decimal("0")
            if existing_ds == Decimal("0"):
                p6 = Decimal("120")
                p6_status = "VERIFIED"
            elif inflows > Decimal("0"):
                stress_ratio = existing_ds / inflows
                if stress_ratio <= Decimal("0.10"): p6 = Decimal("150")
                elif stress_ratio <= Decimal("0.20"): p6 = Decimal("120")
                elif stress_ratio <= Decimal("0.30"): p6 = Decimal("90")
                elif stress_ratio <= Decimal("0.40"): p6 = Decimal("60")
                elif stress_ratio <= Decimal("0.50"): p6 = Decimal("30")
                else: p6 = Decimal("0")
                p6_status = "VERIFIED"
            else:
                p6 = Decimal("0")
                p6_status = "MISSING_DATA"

        vyapar_credit_health_score = int((p1 + p2 + p3 + p4 + p5 + p6).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        fhi_dec = (Decimal(str(vyapar_credit_health_score)) / Decimal("9")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        disclaimer = (
            "Vyapar Credit Health Score and Financial Health Index are proprietary institutional diagnostic indicators "
            "generated by the Vyapar Pulse decision engine for internal assessment and capacity estimation. "
            "They do not constitute an official credit bureau score (such as CIBIL, Experian, CRIF High Mark, or Equifax) "
            "and are not a credit rating under SEBI or RBI credit rating agency regulations."
        )

        fhi_breakdown = {
            "operating_resilience": {
                "score": float(p1),
                "max_score": 150.0,
                "weight_pct": 16.67,
                "status": p1_status
            },
            "cash_flow_health": {
                "score": float(p2),
                "max_score": 150.0,
                "weight_pct": 16.67,
                "status": p2_status
            },
            "margin_stability": {
                "score": float(p3),
                "max_score": 150.0,
                "weight_pct": 16.67,
                "status": p3_status
            },
            "working_capital_velocity": {
                "score": float(p4),
                "max_score": 150.0,
                "weight_pct": 16.67,
                "status": p4_status
            },
            "gst_compliance": {
                "score": float(p5),
                "max_score": 150.0,
                "weight_pct": 16.67,
                "status": p5_status
            },
            "obligation_discipline": {
                "score": float(p6),
                "max_score": 150.0,
                "weight_pct": 16.67,
                "status": p6_status
            },
        }

        return {
            "financial_health_index": fhi_dec,
            "vyapar_credit_health_score": vyapar_credit_health_score,
            "fhi_breakdown": fhi_breakdown,
            "credit_health_disclaimer": disclaimer,
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
