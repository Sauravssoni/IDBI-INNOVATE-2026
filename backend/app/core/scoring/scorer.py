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

        total_score = int((health_score + evidence_score + resilience_score) * Decimal("3"))
        if total_score >= 750:
            band = "A"
        elif total_score >= 700:
            band = "A-"
        elif total_score >= 650:
            band = "B+"
        elif total_score >= 600:
            band = "B"
        else:
            band = "C"

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
            "total_score": total_score,
            "band": band,
        }

    def _compute_financial_health(self) -> Decimal:
        """
        Base: 50
        + GST Bank Reconciliation (max 30)
        + Revenue Trend (max 20)
        """
        score = Decimal("50.0")

        recon = self.features.get("reconciliation_metrics", {})
        ratio = Decimal(str(recon.get("gst_bank_ratio", 0)))

        if Decimal("0.9") <= ratio <= Decimal("1.1"):
            score += Decimal("30")
        elif Decimal("0.8") <= ratio <= Decimal("1.2"):
            score += Decimal("20")
        elif Decimal("0.7") <= ratio <= Decimal("1.3"):
            score += Decimal("10")

        gst = self.features.get("gst_metrics", {})
        trend = gst.get("trend", "UNKNOWN")
        if trend == "GROWING":
            score += Decimal("20")
        elif trend == "STABLE":
            score += Decimal("10")

        return min(max(score, Decimal("0.0")), Decimal("100.0"))

    def _compute_evidence_confidence(self) -> Decimal:
        """
        Based on number of data sources and months of history.
        """
        score = Decimal("0.0")

        gst = self.features.get("gst_metrics", {})
        months = int(gst.get("months_filed", 0))

        if months >= 18:
            score += Decimal("60")
        elif months >= 12:
            score += Decimal("40")
        elif months >= 6:
            score += Decimal("20")

        emp = self.features.get("employment_metrics", {})
        if int(emp.get("months_filed", 0)) > 6:
            score += Decimal("20")

        inv = self.features.get("receivable_metrics", {})
        if int(inv.get("total_invoices", 0)) > 10:
            score += Decimal("20")

        return min(max(score, Decimal("0.0")), Decimal("100.0"))

    def _compute_resilience(self) -> Decimal:
        """
        Penalized by buyer concentration and payment delays.
        Base 100, deduct for risks.
        """
        score = Decimal("100.0")

        inv = self.features.get("receivable_metrics", {})
        concentration = Decimal(str(inv.get("top_buyer_concentration", "1.0")))

        if concentration > Decimal("0.6"):
            score -= Decimal("40")
        elif concentration > Decimal("0.4"):
            score -= Decimal("20")
        elif concentration > Decimal("0.2"):
            score -= Decimal("10")

        delay = int(inv.get("avg_payment_delay_days", 0))
        if delay > 60:
            score -= Decimal("30")
        elif delay > 30:
            score -= Decimal("15")

        gst = self.features.get("gst_metrics", {})
        cv = Decimal(str(gst.get("revenue_cv", "1.0")))

        if cv > Decimal("0.3"):
            score -= Decimal("20")
        elif cv > Decimal("0.15"):
            score -= Decimal("10")

        return min(max(score, Decimal("0.0")), Decimal("100.0"))
