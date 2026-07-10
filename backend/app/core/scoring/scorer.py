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
