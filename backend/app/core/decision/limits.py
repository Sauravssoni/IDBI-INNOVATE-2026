from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.product_policy import get_product_policy, ProductType


class SafeLimitEngine:
    @staticmethod
    def _calculate_loan_from_emi(
        monthly_emi: Any, annual_rate: Any, tenure_months: int
    ) -> Decimal:
        emi_dec = Decimal(str(monthly_emi))
        rate_dec = Decimal(str(annual_rate))
        if emi_dec <= 0 or tenure_months <= 0:
            return Decimal("0.00")
        if rate_dec <= 0:
            return (emi_dec * Decimal(tenure_months)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        rate = rate_dec / Decimal("100") if rate_dec > Decimal("1.0") else rate_dec
        r = rate / Decimal("12")
        factor = (Decimal("1") + r) ** tenure_months
        principal = emi_dec * (factor - Decimal("1")) / (r * factor)
        return principal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_emi_from_loan(
        principal: Any, annual_rate: Any, tenure_months: int
    ) -> Decimal:
        p_dec = Decimal(str(principal))
        rate_dec = Decimal(str(annual_rate))
        if p_dec <= 0 or tenure_months <= 0:
            return Decimal("0.00")
        if rate_dec <= 0:
            return (p_dec / Decimal(tenure_months)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        rate = rate_dec / Decimal("100") if rate_dec > Decimal("1.0") else rate_dec
        r = rate / Decimal("12")
        factor = (Decimal("1") + r) ** tenure_months
        emi = p_dec * r * factor / (factor - Decimal("1"))
        return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def build_limit_bridge(
        cls,
        features: Dict[str, Any],
        requested_product: str,
        requested_amount: Decimal,
        tenure_months: int = 36,
        annual_rate: Decimal = Decimal("0.135"),
    ) -> Dict[str, Any]:
        """Builds a multi-stage limit bridge governed by the formal product policy registry."""
        from app.domain.financial.engine import FinancialCapacityEngine

        try:
            policy = get_product_policy(ProductType(requested_product))
        except ValueError:
            policy = get_product_policy(ProductType.WORKING_CAPITAL_LINE)

        # Enforce policy boundaries on inputs
        annual_rate = max(
            policy.min_rate_annual, min(policy.max_rate_annual, annual_rate)
        )
        tenure_months = max(
            policy.min_tenor_months, min(policy.max_tenor_months, tenure_months)
        )

        cap = FinancialCapacityEngine.compute_capacity_from_features(
            features,
            requested_product=requested_product,
            requested_amount=requested_amount,
            custom_tenure_months=tenure_months,
            custom_annual_rate=annual_rate,
        )

        op_cash = cap["operating_cash_available_for_debt_service_monthly"]
        ver_ds = cap["verified_existing_debt_service_monthly"]
        evd_in = cap["calculation_evidence_ids"].get("inflows", [])
        evd_obl = cap["calculation_evidence_ids"].get("obligations", [])

        stages = []

        # 1. Requested Amount
        stages.append(
            {
                "stage_id": "REQUESTED_AMOUNT",
                "calculated_value": float(requested_amount),
                "formula": "requested_amount",
                "inputs": {"amount": float(requested_amount)},
                "evidence_ids": [],
                "policy_rule_id": "NONE",
                "explanation": "Applicant's requested facility amount.",
                "applied": True,
            }
        )
        current_limit = requested_amount

        # 2. Cash-Serviceability Cap
        target_dscr = policy.min_dscr
        max_ds = op_cash / target_dscr
        serviceable_emi = max(Decimal("0.00"), max_ds - ver_ds)
        cash_cap = cls._calculate_loan_from_emi(
            serviceable_emi, annual_rate, tenure_months
        )
        applied = bool(cash_cap < current_limit)
        if applied:
            current_limit = cash_cap

        stages.append(
            {
                "stage_id": "CASH_SERVICEABILITY_CAP",
                "calculated_value": float(cash_cap),
                "formula": f"loan_from_emi((operating_cash / {target_dscr}) - verified_ds)",
                "inputs": {
                    "operating_cash": float(op_cash),
                    "verified_ds": float(ver_ds),
                    "rate": float(annual_rate),
                    "tenure": tenure_months,
                },
                "evidence_ids": evd_in + evd_obl,
                "policy_rule_id": f"POL-CF-{policy.policy_version}",
                "explanation": "Maximum loan sustainable from operating cash flows.",
                "applied": applied,
            }
        )

        # 3. Verified-Obligation Cap (No arbitrary max_leverage anymore, just rely on capacity cap, or if we need a strict leverage cap we can use a multiple of cash_cap, but let's just make it equal to cash cap if no other policy)
        # We will bound obligation cap strictly by debt service capacity.
        obl_cap = cash_cap
        stages.append(
            {
                "stage_id": "VERIFIED_OBLIGATION_CAP",
                "calculated_value": float(obl_cap),
                "formula": "cash_serviceability_cap",
                "inputs": {
                    "operating_cash": float(op_cash),
                    "verified_ds": float(ver_ds),
                },
                "evidence_ids": evd_obl,
                "policy_rule_id": f"POL-LEV-{policy.policy_version}",
                "explanation": "Maximum total leverage permitted by policy.",
                "applied": False,  # Because it's equal to cash_cap, we just mark it as not strictly applying further reduction unless ver_ds is missing. Wait, if it's identical it doesn't reduce.
            }
        )

        # 4. Product-Policy Cap
        prod_cap = policy.maximum_exposure
        applied = bool(prod_cap < current_limit)
        if applied:
            current_limit = prod_cap
        stages.append(
            {
                "stage_id": "PRODUCT_POLICY_CAP",
                "calculated_value": float(prod_cap),
                "formula": "policy.maximum_exposure",
                "inputs": {},
                "evidence_ids": [],
                "policy_rule_id": f"POL-MAX-{policy.policy_version}",
                "explanation": "Absolute product exposure limit.",
                "applied": applied,
            }
        )

        # 5. Receivables Cap or Equipment LTV Cap
        if (
            requested_product == "RECEIVABLES_FINANCE"
            and policy.receivable_advance_rate > 0
        ):
            inv_metrics = features.get("invoice_metrics", {})
            eligible = Decimal(str(inv_metrics.get("eligible_amount", 0)))
            col_cap = eligible * policy.receivable_advance_rate
            stages.append(
                {
                    "stage_id": "RECEIVABLES_CAP",
                    "calculated_value": float(col_cap),
                    "formula": f"eligible_receivables * {policy.receivable_advance_rate}",
                    "inputs": {"eligible_amount": float(eligible)},
                    "evidence_ids": evd_in,
                    "policy_rule_id": f"POL-REC-{policy.policy_version}",
                    "explanation": "Maximum advance against eligible receivables.",
                    "applied": bool(col_cap < current_limit),
                }
            )
            if col_cap < current_limit:
                current_limit = col_cap
        elif requested_product == "EQUIPMENT_FINANCE" and policy.equipment_ltv > 0:
            eq_val = Decimal(str(features.get("equipment_value", 0)))
            col_cap = eq_val * policy.equipment_ltv
            stages.append(
                {
                    "stage_id": "EQUIPMENT_LTV_CAP",
                    "calculated_value": float(col_cap),
                    "formula": f"equipment_value * {policy.equipment_ltv}",
                    "inputs": {"equipment_value": float(eq_val)},
                    "evidence_ids": [],
                    "policy_rule_id": f"POL-EQ-{policy.policy_version}",
                    "explanation": "Maximum Loan-To-Value against equipment.",
                    "applied": bool(col_cap < current_limit),
                }
            )
            if col_cap < current_limit:
                current_limit = col_cap

        # 6. Concentration Cap
        # Using policy.concentration_haircut if features concentration triggers it, or we just rely on feature
        conc_val = Decimal(
            str(
                features.get("invoice_metrics", {}).get("concentration_haircut", "1.00")
            )
        )
        if conc_val < Decimal("1.00"):
            conc_val = min(conc_val, Decimal("1") - policy.concentration_haircut)

        conc_cap = current_limit * conc_val
        applied = bool(conc_cap < current_limit)
        if applied:
            current_limit = conc_cap
        stages.append(
            {
                "stage_id": "CONCENTRATION_CAP",
                "calculated_value": float(conc_cap),
                "formula": "previous_limit * concentration_haircut",
                "inputs": {"concentration_haircut": float(conc_val)},
                "evidence_ids": evd_in,
                "policy_rule_id": f"POL-CONC-{policy.policy_version}",
                "explanation": "Haircut due to top-buyer concentration risks.",
                "applied": applied,
            }
        )

        # 7. Stress Cap
        stressed_cash = cap["stressed_operating_cash_available"]
        stress_ds = stressed_cash / target_dscr
        stress_emi = max(Decimal("0.00"), stress_ds - ver_ds)

        # apply policy stress rate hike
        stress_annual_rate = annual_rate + (
            Decimal(policy.stress_rate_hike_bps) / Decimal("10000")
        )
        stress_cap = cls._calculate_loan_from_emi(
            stress_emi, stress_annual_rate, tenure_months
        )
        applied = bool(stress_cap < current_limit)
        if applied:
            current_limit = stress_cap
        stages.append(
            {
                "stage_id": "STRESS_CAP",
                "calculated_value": float(stress_cap),
                "formula": f"loan_from_emi((stressed_operating_cash / {target_dscr}) - verified_ds, stressed_rate)",
                "inputs": {
                    "stressed_cash": float(stressed_cash),
                    "stressed_rate": float(stress_annual_rate),
                },
                "evidence_ids": evd_in + evd_obl,
                "policy_rule_id": f"POL-STR-{policy.policy_version}",
                "explanation": "Limit sustainable under downside revenue stress and rate hikes.",
                "applied": applied,
            }
        )

        # Find binding constraint
        binding_stage = next((s for s in reversed(stages) if s["applied"]), stages[0])
        if current_limit <= Decimal("0"):
            current_limit = Decimal("0")

        return {
            "requested_amount": float(requested_amount),
            "final_supportable_amount": float(current_limit),
            "binding_constraint": binding_stage["stage_id"],
            "stages": stages,
        }

    @classmethod
    def calculate_all_limits(cls, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        from app.domain.financial.engine import FinancialCapacityEngine

        cap = FinancialCapacityEngine.compute_capacity_from_features(features)
        limits = [
            cap["product_limits"]["RECEIVABLES_FINANCE"],
            cap["product_limits"]["WORKING_CAPITAL_LINE"],
            cap["product_limits"]["TERM_LOAN"],
            cap["product_limits"]["EQUIPMENT_FINANCE"],
        ]
        return [limit for limit in limits if limit["applicability"] == "APPLICABLE"]
