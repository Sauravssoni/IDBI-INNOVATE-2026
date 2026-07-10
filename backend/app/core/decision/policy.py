from typing import Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.limits import SafeLimitEngine
from app.db.orm.cases import SystemRecommendation
from app.core.versions import POLICY_VERSION, CALCULATION_VERSION


class DecisionPolicy:
    """
    Applies banking policy rules to computed scores and features
    to generate deterministic decisions and safe limits.
    """

    def __init__(
        self,
        features: Dict[str, Any],
        scores: Dict[str, Any],
        requested_amount: Decimal,
        requested_product: str,
    ):
        self.features = features
        self.scores = scores
        self.requested_amount = requested_amount
        self.requested_product = requested_product

    def evaluate(self) -> Dict[str, Any]:
        # 1. Base Checks (Precedence)
        consent_status = self.features.get("consent_status", "VALID")
        if consent_status != "VALID":
            return {
                "decision": "BLOCK_PROCESSING",
                "reasons": ["Invalid, revoked or expired consent"],
                "offers": [],
                "binding_limit": Decimal("0"),
                "post_loan_dscr": None,
            }

        integrity_flag = self.features.get("integrity_flag", False)
        if integrity_flag:
            return {
                "decision": SystemRecommendation.ENHANCED_DUE_DILIGENCE.value,
                "reasons": ["Material integrity/fraud flag detected"],
                "offers": [],
                "binding_limit": Decimal("0"),
                "post_loan_dscr": None,
            }

        evidence_confidence = Decimal(
            str(self.scores.get("evidence_confidence_score", 0))
        )
        decision_threshold = Decimal("40.0")
        if evidence_confidence < decision_threshold:
            return {
                "decision": SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value,
                "reasons": ["Evidence confidence below configured decision threshold"],
                "offers": [],
                "binding_limit": Decimal("0"),
                "post_loan_dscr": None,
            }

        # 1.5 Basic DSCR Check
        bank_metrics = self.features.get("bank_metrics", {})
        dscr_str = bank_metrics.get("dscr")
        if dscr_str is not None:
            dscr = Decimal(dscr_str)
            if dscr < Decimal("1.15"):
                return {
                    "decision": SystemRecommendation.DECLINE_RECOMMENDED.value,
                    "reasons": [
                        f"Debt Service Coverage Ratio (DSCR) of {dscr:.2f} is below minimum requirement of 1.15"
                    ],
                    "offers": [],
                    "binding_limit": Decimal("0"),
                    "post_loan_dscr": None,
                }

        # 2. Capacity & Limits Calculation
        applicable_limits = SafeLimitEngine.calculate_all_limits(self.features)

        if not applicable_limits:
            return {
                "decision": SystemRecommendation.DECLINE_RECOMMENDED.value,
                "reasons": [
                    "Financial capacity inadequate and no currently viable alternative"
                ],
                "offers": [],
                "binding_limit": Decimal("0"),
                "post_loan_dscr": None,
            }

        # The binding limit for the case is the minimum of all applicable limits to be safe
        binding_limit = min(limit["calculated_limit"] for limit in applicable_limits)

        # Determine the product-specific limit if applicable, otherwise use binding limit
        product_limit = binding_limit
        for limit in applicable_limits:
            # Map requested_product to method if possible, here simplified
            if (
                "WORKING_CAPITAL" in self.requested_product.upper()
                and limit["method"] == "WORKING_CAPITAL_LINE"
            ):
                product_limit = limit["calculated_limit"]

        # 3. Offer Generation
        offers = self._generate_offers(product_limit, self.requested_product)

        # 4. Final Recommendation Precedence
        # Rule 5: Requested structure unsupported but viable alternatives exist
        if self.requested_amount > product_limit:
            decision = SystemRecommendation.CONDITIONAL_OFFER.value
            reasons = [
                f"Requested amount ({self.requested_amount}) exceeds supportable limit ({product_limit}). Offering alternatives."
            ]
        # Rule 6: Requested structure supportable with sufficient evidence
        else:
            decision = SystemRecommendation.READY_FOR_REVIEW.value
            reasons = ["Requested structure supportable."]

        requested_emi = self._calculate_emi(self.requested_amount, 36)
        _, _, post_loan_dscr_req = self._derive_offer_dscrs(requested_emi)

        return {
            "decision": decision,
            "reasons": reasons,
            "offers": offers,
            "binding_limit": product_limit,
            "limit_details": applicable_limits,
            "post_loan_dscr": post_loan_dscr_req,
        }

    def _calculate_emi(
        self,
        principal: Decimal,
        tenure_months: int,
        annual_rate: Decimal = Decimal("0.135"),
    ) -> Decimal:
        return SafeLimitEngine.calculate_emi_from_loan(principal, annual_rate, tenure_months)

    def _derive_offer_dscrs(self, emi: Decimal) -> Tuple[str, str, str]:
        bank = self.features.get("bank_metrics", {})
        try:
            credits = Decimal(str(bank.get("avg_monthly_credits", "0")))
            debits = Decimal(str(bank.get("avg_monthly_debits", "0")))
            dscr_str = bank.get("dscr")
            if dscr_str and Decimal(str(dscr_str)) > 0:
                existing_obligations = credits / Decimal(str(dscr_str))
            elif debits > 0:
                existing_obligations = debits * Decimal("0.20")
            else:
                existing_obligations = Decimal("0")
        except Exception:
            return ("UNKNOWN", "UNKNOWN", "UNKNOWN")

        total_obligations = existing_obligations + emi
        if total_obligations <= 0 or credits <= 0:
            return ("UNKNOWN", "UNKNOWN", "UNKNOWN")

        pre_loan_dscr = credits / existing_obligations if existing_obligations > 0 else (credits / total_obligations)
        post_loan_dscr = credits / total_obligations
        stressed_inflows = credits * Decimal("0.80")
        stressed_obligations = total_obligations * Decimal("1.15")
        stressed_dscr = (
            stressed_inflows / stressed_obligations
            if stressed_obligations > 0
            else Decimal("0.00")
        )

        pre_str = str(pre_loan_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        stressed_str = str(stressed_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        post_str = str(post_loan_dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return (pre_str, stressed_str, post_str)

    def _generate_offers(
        self, binding_limit: Decimal, product_type: str
    ) -> List[Dict[str, Any]]:
        offers = []
        common_evidence_refs = [
            "Bank Statement Account Feed (Observed transaction history)",
            "GST Returns Corroboration Feed",
            "Credit Twin Cash-Flow Verification Engine",
        ]
        rate_label = "Sandbox illustrative rate assumption: 13.5% p.a."

        # CONSERVATIVE
        conservative_amount = (binding_limit * Decimal("0.6")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        conservative_emi = self._calculate_emi(conservative_amount, 12)
        base_dscr_c, stressed_dscr_c, post_loan_dscr_c = self._derive_offer_dscrs(conservative_emi)
        offers.append(
            {
                "tier": "CONSERVATIVE",
                "currency": "INR",
                "amount": str(conservative_amount),
                "product_type": product_type,
                "tenure_months": 12,
                "repayment_frequency": "MONTHLY",
                "estimated_repayment": str(conservative_emi),
                "base_dscr": base_dscr_c,
                "stressed_dscr": stressed_dscr_c,
                "post_loan_dscr": post_loan_dscr_c,
                "liquidity_impact": "LOW",
                "applicable_capacity_ceilings": [str(binding_limit)],
                "binding_ceiling": str(binding_limit),
                "conditions": ["Quarterly GST submission", rate_label],
                "evidence_references": common_evidence_refs,
                "policy_version": POLICY_VERSION,
                "calculation_version": CALCULATION_VERSION,
                "human_review_required": True,
            }
        )

        # BALANCED
        balanced_amount = (binding_limit * Decimal("0.8")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        balanced_emi = self._calculate_emi(balanced_amount, 24)
        base_dscr_b, stressed_dscr_b, post_loan_dscr_b = self._derive_offer_dscrs(balanced_emi)
        offers.append(
            {
                "tier": "BALANCED",
                "currency": "INR",
                "amount": str(balanced_amount),
                "product_type": product_type,
                "tenure_months": 24,
                "repayment_frequency": "MONTHLY",
                "estimated_repayment": str(balanced_emi),
                "base_dscr": base_dscr_b,
                "stressed_dscr": stressed_dscr_b,
                "post_loan_dscr": post_loan_dscr_b,
                "liquidity_impact": "MEDIUM",
                "applicable_capacity_ceilings": [str(binding_limit)],
                "binding_ceiling": str(binding_limit),
                "conditions": [
                    "Monthly AA sync",
                    "Quarterly GST submission",
                    rate_label,
                ],
                "evidence_references": common_evidence_refs,
                "policy_version": POLICY_VERSION,
                "calculation_version": CALCULATION_VERSION,
                "human_review_required": True,
            }
        )

        # GROWTH
        growth_amount = binding_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        growth_emi = self._calculate_emi(growth_amount, 36)
        base_dscr_g, stressed_dscr_g, post_loan_dscr_g = self._derive_offer_dscrs(growth_emi)
        offers.append(
            {
                "tier": "GROWTH",
                "currency": "INR",
                "amount": str(growth_amount),
                "product_type": product_type,
                "tenure_months": 36,
                "repayment_frequency": "MONTHLY",
                "estimated_repayment": str(growth_emi),
                "base_dscr": base_dscr_g,
                "stressed_dscr": stressed_dscr_g,
                "post_loan_dscr": post_loan_dscr_g,
                "liquidity_impact": "HIGH",
                "applicable_capacity_ceilings": [str(binding_limit)],
                "binding_ceiling": str(binding_limit),
                "conditions": [
                    "Monthly AA sync",
                    "Monthly GST submission",
                    "Escrow routing required",
                    rate_label,
                ],
                "evidence_references": common_evidence_refs,
                "policy_version": POLICY_VERSION,
                "calculation_version": CALCULATION_VERSION,
                "human_review_required": True,
            }
        )

        return offers
