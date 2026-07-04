from __future__ import annotations
from typing import Literal

from dataclasses import dataclass
from hashlib import sha256

from .models import (
    Assessment,
    BusinessProfile,
    CreditStructure,
    Driver,
    ScenarioRequest,
    ScenarioResult,
)


MODEL_VERSION = "vp-core-0.1.0"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def linear(value: float, bad: float, good: float) -> float:
    if good == bad:
        return 0.5
    return clamp((value - bad) / (good - bad))


def inverse_linear(value: float, good: float, bad: float) -> float:
    return 1.0 - linear(value, good, bad)


def ratio_alignment(ratio: float) -> float:
    # Best when banking inflows broadly reconcile to GST turnover.
    return clamp(1 - abs(ratio - 1.0) / 0.55)


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    value: float
    weight: float
    evidence: str


class CreditEngine:
    """Transparent baseline engine designed to be replaced by validated models.

    This baseline deliberately separates financial health from data confidence.
    It supports abstention when evidence quality is insufficient.
    """

    def assess(self, p: BusinessProfile) -> Assessment:
        features = self._features(p)
        weighted = sum(f.value * f.weight for f in features)
        total_weight = sum(f.weight for f in features)
        health = round(100 * weighted / total_weight)

        confidence = round(
            100
            * (
                0.30 * p.data_quality.completeness
                + 0.22 * p.data_quality.recency
                + 0.25 * p.data_quality.cross_source_agreement
                + 0.18 * p.data_quality.identity_match
                + 0.05 * (1 - p.data_quality.anomaly_risk)
            )
        )

        resilience = round(
            100
            * (
                0.30 * linear(p.cash_buffer_days, 3, 60)
                + 0.28 * linear(p.dscr, 0.8, 2.2)
                + 0.18 * inverse_linear(p.revenue_volatility, 0.08, 0.80)
                + 0.14 * inverse_linear(p.largest_buyer_share, 0.15, 0.75)
                + 0.10 * inverse_linear(p.receivable_days, 20, 150)
            )
        )

        drivers = self._drivers(features)
        structure = self._decision(p, health, confidence, resilience)
        actions = self._bankability_actions(p, health, confidence)
        warnings = self._warnings(p, confidence)
        assessment_id = self._assessment_id(p, health, confidence)

        return Assessment(
            assessment_id=assessment_id,
            business_id=p.business_id,
            financial_health_score=health,
            data_confidence_score=confidence,
            resilience_score=resilience,
            risk_band=self._band(health, confidence),
            decision=structure,
            top_drivers=drivers,
            bankability_actions=actions,
            warnings=warnings,
            model_version=MODEL_VERSION,
        )

    def simulate(self, request: ScenarioRequest) -> ScenarioResult:
        p = request.profile
        baseline = self.assess(p)
        revenue_multiplier = 1 + request.revenue_shock_pct
        delay_pressure = clamp(request.buyer_delay_days / max(p.receivable_days + 30, 30), 0, 1.5)

        stressed_payload = p.model_dump()
        stressed_payload["monthly_revenue_inr"] = max(1, p.monthly_revenue_inr * revenue_multiplier)
        stressed_payload["revenue_growth_6m"] = max(-1, p.revenue_growth_6m + request.revenue_shock_pct)
        stressed_payload["cash_buffer_days"] = max(0, p.cash_buffer_days * revenue_multiplier - 12 * delay_pressure)
        stressed_payload["dscr"] = max(0, p.dscr * revenue_multiplier - 0.25 * delay_pressure)
        stressed_payload["receivable_days"] = min(365, p.receivable_days + request.buyer_delay_days)
        if request.proposed_amount_inr:
            stressed_payload["requested_amount_inr"] = request.proposed_amount_inr
        if request.proposed_tenure_months:
            stressed_payload["requested_tenure_months"] = request.proposed_tenure_months

        stressed_profile = BusinessProfile(**stressed_payload)
        stressed = self.assess(stressed_profile)
        drop = stressed.financial_health_score - baseline.financial_health_score

        if stressed.resilience_score >= 70 and stressed.financial_health_score >= 65:
            recommendation = "Structure remains resilient under the selected stress scenario."
        elif stressed.resilience_score >= 50:
            recommendation = "Reduce exposure or align repayment with the cash-conversion cycle."
        else:
            recommendation = "Do not use the proposed structure; request mitigation, collateral, or additional evidence."

        return ScenarioResult(
            baseline_score=baseline.financial_health_score,
            stressed_score=stressed.financial_health_score,
            score_change=drop,
            stressed_dscr=round(stressed_profile.dscr, 2),
            stressed_cash_buffer_days=round(stressed_profile.cash_buffer_days, 1),
            recommendation=recommendation,
        )

    def _features(self, p: BusinessProfile) -> list[Feature]:
        return [
            Feature("revenue_growth", "Revenue trajectory", linear(p.revenue_growth_6m, -0.20, 0.25), 0.10, f"Six-month growth: {p.revenue_growth_6m:.1%}"),
            Feature("revenue_stability", "Revenue stability", inverse_linear(p.revenue_volatility, 0.08, 0.90), 0.08, f"Revenue volatility index: {p.revenue_volatility:.2f}"),
            Feature("gst_bank_match", "GST-to-bank reconciliation", ratio_alignment(p.bank_inflow_gst_ratio), 0.12, f"Bank inflow/GST ratio: {p.bank_inflow_gst_ratio:.2f}"),
            Feature("gst_regularity", "GST filing regularity", p.gst_filing_regularity, 0.08, f"On-time filing ratio: {p.gst_filing_regularity:.0%}"),
            Feature("cash_buffer", "Liquidity buffer", linear(p.cash_buffer_days, 3, 60), 0.10, f"Estimated cash buffer: {p.cash_buffer_days:.0f} days"),
            Feature("dscr", "Debt service capacity", linear(p.dscr, 0.75, 2.25), 0.13, f"DSCR: {p.dscr:.2f}"),
            Feature("debt_burden", "Debt burden", inverse_linear(p.debt_obligation_ratio, 0.10, 0.65), 0.08, f"Debt obligation ratio: {p.debt_obligation_ratio:.0%}"),
            Feature("repayment_hygiene", "Repayment hygiene", inverse_linear(p.cheque_or_emi_bounce_rate, 0.00, 0.15), 0.10, f"Bounce rate: {p.cheque_or_emi_bounce_rate:.1%}"),
            Feature("receivables", "Receivable efficiency", inverse_linear(p.receivable_days, 20, 150), 0.07, f"Receivable cycle: {p.receivable_days:.0f} days"),
            Feature("buyer_diversity", "Buyer diversification", inverse_linear(p.largest_buyer_share, 0.12, 0.75), 0.07, f"Largest buyer share: {p.largest_buyer_share:.0%}"),
            Feature("vintage", "Operating vintage", linear(p.vintage_months, 6, 60), 0.04, f"Business vintage: {p.vintage_months} months"),
            Feature("bureau", "Bureau evidence", self._bureau_value(p.bureau_score), 0.03, "No bureau history" if p.bureau_score is None else f"Bureau score: {p.bureau_score}"),
        ]

    @staticmethod
    def _bureau_value(score: int | None) -> float:
        # Missing bureau history is treated as unknown, not as an adverse event.
        if score is None:
            return 0.55
        return linear(score, 550, 800)

    @staticmethod
    def _drivers(features: list[Feature]) -> list[Driver]:
        ranked = sorted(features, key=lambda f: abs((f.value - 0.5) * f.weight), reverse=True)
        result: list[Driver] = []
        for f in ranked[:7]:
            signed = (f.value - 0.5) * 2
            result.append(
                Driver(
                    key=f.key,
                    label=f.label,
                    direction="positive" if signed > 0.12 else "negative" if signed < -0.12 else "neutral",
                    impact=round(signed * f.weight * 100, 2),
                    evidence=f.evidence,
                )
            )
        return result

    def _decision(self, p: BusinessProfile, health: int, confidence: int, resilience: int) -> CreditStructure:
        from typing import Literal
        outcome: Literal["eligible", "conditional_offer", "structured_offer", "additional_data_required", "bankability_plan"]
        monthly_free_cash_proxy = p.monthly_revenue_inr * max(0.04, min(0.22, 0.04 + 0.08 * p.dscr))
        tenure_factor = min(p.requested_tenure_months, 36)
        safe_amount = round(monthly_free_cash_proxy * tenure_factor * (0.55 + health / 250), -3)
        safe_amount = max(0.0, min(safe_amount, p.requested_amount_inr))

        product = self._product_fit(p)
        conditions: list[str] = []

        if confidence < 65:
            return CreditStructure(
                outcome="additional_data_required",
                recommended_product="Assessment hold",
                safe_amount_inr=0,
                recommended_tenure_months=p.requested_tenure_months,
                conditions=["Resolve missing or inconsistent evidence before a credit recommendation."],
            )

        if health >= 78 and resilience >= 65:
            outcome = "eligible"
        elif health >= 66:
            outcome = "conditional_offer"
            conditions.append("Enable consented monthly monitoring for the first six months.")
        elif health >= 52:
            outcome = "structured_offer"
            conditions.extend([
                "Use transaction-linked repayment or escrow where policy permits.",
                "Cap exposure at the stress-tested safe amount.",
            ])
        else:
            return CreditStructure(
                outcome="bankability_plan",
                recommended_product="No immediate automated recommendation",
                safe_amount_inr=0,
                recommended_tenure_months=p.requested_tenure_months,
                conditions=["Complete the prioritized bankability actions and reassess."],
            )

        if safe_amount < p.requested_amount_inr * 0.8:
            conditions.append("Requested amount exceeds the current cash-flow-supported exposure.")

        return CreditStructure(
            outcome=outcome,
            recommended_product=product,
            safe_amount_inr=safe_amount,
            recommended_tenure_months=self._tenure_fit(p),
            conditions=conditions,
        )

    @staticmethod
    def _product_fit(p: BusinessProfile) -> str:
        cash_cycle = max(0, p.receivable_days - p.payable_days)
        if cash_cycle >= 45:
            return "Invoice / receivables-linked working capital"
        if p.upi_share >= 0.55 and p.sector in {p.sector.RETAIL, p.sector.FOOD_HOSPITALITY}:
            return "Cash-flow-linked merchant working capital"
        if p.requested_tenure_months > 36:
            return "Term loan subject to asset-use verification"
        return "Cash credit / working-capital line"

    @staticmethod
    def _tenure_fit(p: BusinessProfile) -> int:
        cash_cycle = max(0, p.receivable_days - p.payable_days)
        if cash_cycle > 60:
            return min(max(12, p.requested_tenure_months), 36)
        return min(p.requested_tenure_months, 24)

    @staticmethod
    def _band(health: int, confidence: int) -> Literal["A", "B", "C", "D", "E"]:
        if confidence < 65:
            return "E"
        if health >= 80:
            return "A"
        if health >= 68:
            return "B"
        if health >= 55:
            return "C"
        if health >= 42:
            return "D"
        return "E"

    @staticmethod
    def _bankability_actions(p: BusinessProfile, health: int, confidence: int) -> list[str]:
        actions: list[str] = []
        if p.data_quality.completeness < 0.85:
            actions.append("Connect the missing consented bank/GST periods to improve evidence coverage.")
        if p.data_quality.cross_source_agreement < 0.80 or not 0.82 <= p.bank_inflow_gst_ratio <= 1.18:
            actions.append("Reconcile GST turnover, invoices and bank receipts; explain material mismatches.")
        if p.largest_buyer_share > 0.45:
            actions.append("Reduce single-buyer concentration or provide enforceable purchase-order evidence.")
        if p.receivable_days > 75:
            actions.append("Shorten receivable cycles or route eligible invoices through receivables finance.")
        if p.cash_buffer_days < 20:
            actions.append("Build a minimum operating liquidity buffer of approximately 20–30 days.")
        if p.cheque_or_emi_bounce_rate > 0.03:
            actions.append("Maintain three clean repayment cycles before reassessment.")
        if p.dscr < 1.2:
            actions.append("Lower the requested exposure or extend tenure to restore debt-service headroom.")
        if not actions:
            actions.append("Maintain current filing, repayment and cash-flow discipline; review quarterly.")
        return actions[:5]

    @staticmethod
    def _warnings(p: BusinessProfile, confidence: int) -> list[str]:
        warnings: list[str] = []
        if p.data_quality.anomaly_risk > 0.55:
            warnings.append("Elevated anomaly risk: manual evidence review required.")
        if p.top_5_buyer_share > 0.85:
            warnings.append("High aggregate customer concentration may amplify correlated payment risk.")
        if p.bureau_score is None:
            warnings.append("No bureau history: treated as missing evidence, not as a negative event.")
        if confidence < 65:
            warnings.append("Engine abstained from a credit recommendation due to insufficient confidence.")
        return warnings

    @staticmethod
    def _assessment_id(p: BusinessProfile, health: int, confidence: int) -> str:
        payload = f"{p.business_id}|{health}|{confidence}|{MODEL_VERSION}"
        return "asm_" + sha256(payload.encode()).hexdigest()[:16]
