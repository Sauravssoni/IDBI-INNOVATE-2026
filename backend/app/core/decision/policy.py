from typing import Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.limits import SafeLimitEngine
from app.db.orm.cases import SystemRecommendation
from app.core.versions import POLICY_VERSION, CALCULATION_VERSION
from app.domain.financial.obligations import ASSESSABLE_OBLIGATION_STATES


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
            str(self.scores.get("evidence_confidence_score", 100))
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

        # 1.5 Basic DSCR Check from computed features
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
                    "binding_limit": Decimal("0.00"),
                    "post_loan_dscr": None,
                    "current_dscr": str(dscr),
                }

        # 2. Canonical Capacity & Limits Calculation strictly via FinancialCapacityEngine
        from app.domain.financial.engine import FinancialCapacityEngine

        cap_summary = FinancialCapacityEngine.compute_capacity_from_features(
            self.features, self.requested_amount, self.requested_product
        )

        # Check for material unresolved credit/debit activity first
        summary = bank_metrics.get("transaction_categorization_summary", {})
        if summary.get("has_material_unresolved_activity", False):
            unresolved_inflow_ids = summary.get("unresolved_inflow_ids", [])
            unresolved_outflow_ids = summary.get("unresolved_outflow_ids", [])
            unresolved_inflow_items = summary.get("unresolved_inflow_items", [])
            unresolved_outflow_items = summary.get("unresolved_outflow_items", [])
            reasons = []
            if (
                len(unresolved_inflow_ids) > 0
                or summary.get("unresolved_credit_ratio", 0) > 0.05
            ):
                reasons.append(
                    f"UNRESOLVED_CREDIT_TRANSACTIONS: {len(unresolved_inflow_ids)} unrecognised credit items require manual categorization or evidence."
                )
            if (
                len(unresolved_outflow_ids) > 0
                or summary.get("unresolved_debit_ratio", 0) > 0.05
            ):
                reasons.append(
                    f"UNRESOLVED_DEBIT_TRANSACTIONS: {len(unresolved_outflow_ids)} unrecognised debit items require manual categorization or evidence."
                )
            if not reasons:
                reasons.append(
                    "UNRESOLVED_CREDIT_TRANSACTIONS: Unrecognised bank transactions exceed materiality threshold."
                )
            return {
                "decision": SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value,
                "reasons": reasons,
                "offers": [],
                "binding_limit": Decimal("0.00"),
                "post_loan_dscr": None,
                "current_dscr": None,
                "missing_verification_state": "UNRESOLVED_CREDIT_TRANSACTIONS"
                if len(unresolved_inflow_ids) > 0
                else "UNRESOLVED_DEBIT_TRANSACTIONS",
                "evidence_checklist": [
                    "Manual categorization of unrecognised bank transactions via Account Aggregator feed",
                    "Audited financial notes or ledger corroboration for unresolved cash movements",
                ],
                "unresolved_transaction_details": {
                    "unresolved_inflow_items": unresolved_inflow_items,
                    "unresolved_outflow_items": unresolved_outflow_items,
                    "unresolved_inflow_count": len(unresolved_inflow_ids),
                    "unresolved_outflow_count": len(unresolved_outflow_ids),
                },
            }

        # Check for insufficient cash flow data
        if cap_summary.get("cash_flow_status") == "INSUFFICIENT_CASH_FLOW_DATA":
            return {
                "decision": SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value,
                "reasons": [
                    "INSUFFICIENT_CASH_FLOW_DATA: No recognised whitelisted operating cash flows in bank statements or GST returns."
                ],
                "offers": [],
                "binding_limit": Decimal("0.00"),
                "post_loan_dscr": None,
                "current_dscr": None,
                "missing_verification_state": "INSUFFICIENT_CASH_FLOW_DATA",
                "evidence_checklist": [
                    "Verified 12-month Bank Statement Account Feed with whitelisted operating categories",
                    "Authentic GST Returns (GSTR-1 / GSTR-3B) Corroboration Feed",
                ],
            }

        # Check for unverified existing debt obligations (strict check: never CONDITIONAL_OFFER for unknown obligations)
        obligation_state = cap_summary.get("obligation_verification_state")
        if obligation_state not in ASSESSABLE_OBLIGATION_STATES:
            return {
                "decision": SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value,
                "reasons": [
                    f"UNVERIFIED_EXISTING_OBLIGATIONS: Existing debt service obligations ({obligation_state}) are unverified."
                ],
                "offers": [],
                "binding_limit": Decimal("0.00"),
                "post_loan_dscr": None,
                "current_dscr": None,
                "missing_verification_state": "UNVERIFIED_EXISTING_OBLIGATIONS",
                "evidence_checklist": [
                    "Authentic Commercial CIBIL / Bureau Report verifying exact existing monthly EMI burden",
                    "Verified loan sanction letters or bank statement repayment track for all debt service deductions",
                ],
            }

        product_limits_dict = cap_summary.get("product_limits", {})
        applicable_limits = [
            limit
            for limit in product_limits_dict.values()
            if isinstance(limit, dict) and limit.get("applicability") == "APPLICABLE"
        ]

        if not applicable_limits:
            return {
                "decision": SystemRecommendation.DECLINE_RECOMMENDED.value,
                "reasons": [
                    "Financial capacity inadequate and no currently viable alternative"
                ],
                "offers": [],
                "binding_limit": Decimal("0.00"),
                "post_loan_dscr": None,
                "current_dscr": cap_summary.get("current_dscr"),
            }

        product_limit_val = cap_summary.get("binding_product_limit")
        product_limit = (
            Decimal(str(product_limit_val))
            if product_limit_val is not None
            else Decimal("0.00")
        )
        if product_limit <= 0 and applicable_limits:
            product_limit = max(
                Decimal(str(limit.get("calculated_limit", "0.00")))
                for limit in applicable_limits
            )

        if product_limit <= 0:
            return {
                "decision": SystemRecommendation.DECLINE_RECOMMENDED.value,
                "reasons": [
                    f"Financial capacity inadequate under target DSCR criteria (Current DSCR: {cap_summary.get('current_dscr', 'N/A')})"
                ],
                "offers": [],
                "binding_limit": Decimal("0.00"),
                "post_loan_dscr": None,
                "current_dscr": cap_summary.get("current_dscr"),
            }

        # 3. Canonical Structural Offer Generation
        offers = self._generate_offers(cap_summary)

        # 4. Final Recommendation Precedence
        if self.requested_amount > product_limit:
            decision = SystemRecommendation.CONDITIONAL_OFFER.value
            reasons = [
                f"Requested amount ({self.requested_amount}) exceeds supportable limit ({product_limit}). Offering alternatives."
            ]
        else:
            decision = SystemRecommendation.READY_FOR_REVIEW.value
            reasons = ["Requested structure supportable."]

        requested_emi = self._calculate_emi(self.requested_amount, 36)
        _, _, post_loan_dscr_req = self._derive_offer_dscrs(cap_summary, requested_emi)

        return {
            "decision": decision,
            "reasons": reasons,
            "offers": offers,
            "binding_limit": product_limit,
            "limit_details": applicable_limits,
            "post_loan_dscr": post_loan_dscr_req,
            "current_dscr": cap_summary.get("current_dscr"),
        }

    def _calculate_emi(
        self,
        principal: Decimal,
        tenure_months: int,
        annual_rate: Decimal = Decimal("0.135"),
    ) -> Decimal:
        return SafeLimitEngine.calculate_emi_from_loan(
            principal, annual_rate, tenure_months
        )

    def _derive_offer_dscrs(
        self, cap: Dict[str, Any], emi: Decimal
    ) -> Tuple[str, str, str]:
        if cap.get("obligation_verification_state") not in ASSESSABLE_OBLIGATION_STATES:
            return ("UNKNOWN", "UNKNOWN", "UNKNOWN")

        current_dscr = cap.get("current_dscr")
        pre_str = str(current_dscr) if current_dscr is not None else "UNKNOWN"

        noi_val = cap.get(
            "operating_cash_available_for_debt_service_monthly", Decimal("0.00")
        )
        noi = Decimal(str(noi_val)) if noi_val is not None else Decimal("0.00")
        existing_ds_val = cap.get(
            "verified_existing_debt_service_monthly", Decimal("0.00")
        )
        existing_ds = (
            Decimal(str(existing_ds_val))
            if existing_ds_val is not None
            else Decimal("0.00")
        )
        total_ds = existing_ds + emi

        if total_ds > 0 and noi > 0:
            post_dscr = (noi / total_ds).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            post_str = str(post_dscr)
        else:
            post_str = "UNKNOWN"

        stressed_dscr = cap.get("stressed_dscr")
        stressed_str = str(stressed_dscr) if stressed_dscr is not None else "UNKNOWN"

        return (pre_str, stressed_str, post_str)

    def _generate_offers(self, cap_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        offers = []
        product_limits = cap_summary.get("product_limits", {})
        common_evidence_refs = [
            "Bank Statement Account Feed (Observed transaction history)",
            "GST Returns Corroboration Feed",
            "Credit Twin Cash-Flow Verification Engine",
        ]
        max_borrowing_val = cap_summary.get("max_borrowing_limit", Decimal("0.00"))
        max_borrowing_dec = (
            Decimal(str(max_borrowing_val))
            if max_borrowing_val is not None
            else Decimal("0.00")
        )

        # 1. WORKING_CAPITAL_LINE
        wc_info = product_limits.get("WORKING_CAPITAL_LINE", {})
        wc_limit = (
            Decimal(str(wc_info.get("calculated_limit", "0.00")))
            if isinstance(wc_info, dict)
            else Decimal("0.00")
        )
        if wc_limit <= 0 or (
            isinstance(wc_info, dict)
            and wc_info.get("applicability") == "NOT_APPLICABLE"
        ):
            wc_limit = Decimal("0.00")
        elif max_borrowing_dec > 0 and wc_limit > max_borrowing_dec:
            wc_limit = max_borrowing_dec.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        wc_tenure = (
            wc_info.get("tenure_months", 12) if isinstance(wc_info, dict) else 12
        )
        wc_rate = (
            wc_info.get("interest_rate_pct", 12.0)
            if isinstance(wc_info, dict)
            else 12.0
        )
        wc_emi = self._calculate_emi(
            wc_limit, wc_tenure, Decimal(str(wc_rate)) / Decimal("100")
        )
        base_dscr_wc, stressed_dscr_wc, post_loan_dscr_wc = self._derive_offer_dscrs(
            cap_summary, wc_emi
        )

        offers.append(
            {
                "tier": "CONSERVATIVE",
                "currency": "INR",
                "amount": str(wc_limit),
                "product_type": "WORKING_CAPITAL_LINE",
                "tenure_months": wc_tenure,
                "interest_rate_pct": float(wc_rate),
                "repayment_frequency": "MONTHLY_INTEREST_ONLY",
                "estimated_repayment": str(wc_emi),
                "base_dscr": base_dscr_wc,
                "stressed_dscr": stressed_dscr_wc,
                "post_loan_dscr": post_loan_dscr_wc,
                "collateral_structure": "First charge on all current assets (Stocks & Book Debts)",
                "covenants": [
                    "Monthly Stock and Debtors Statement submission within 15 days",
                    "Drawing power inspection quarterly",
                    "Monthly GST returns (GSTR-1 & GSTR-3B) sync",
                ],
                "evidence_checklist": [
                    "12-month Bank Statement Account Feed",
                    "GSTR-1 & GSTR-3B filings for past 12 months",
                    "Latest Stock & Book Debt Aging Report",
                ],
                "liquidity_impact": "LOW",
                "applicable_capacity_ceilings": [str(wc_limit)],
                "binding_ceiling": str(wc_limit),
                "conditions": [
                    "Quarterly GST submission",
                    f"Product rate: {wc_rate}% p.a.",
                ],
                "evidence_references": common_evidence_refs,
                "policy_version": POLICY_VERSION,
                "calculation_version": CALCULATION_VERSION,
                "human_review_required": True,
            }
        )

        # 2. TERM_LOAN
        tl_info = product_limits.get("TERM_LOAN", {})
        tl_limit = (
            Decimal(str(tl_info.get("calculated_limit", "0.00")))
            if isinstance(tl_info, dict)
            else Decimal("0.00")
        )
        if tl_limit <= 0 or (
            isinstance(tl_info, dict)
            and tl_info.get("applicability") == "NOT_APPLICABLE"
        ):
            tl_limit = Decimal("0.00")
        elif max_borrowing_dec > 0 and tl_limit > max_borrowing_dec:
            tl_limit = max_borrowing_dec.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        tl_tenure = (
            tl_info.get("tenure_months", 36) if isinstance(tl_info, dict) else 36
        )
        tl_rate = (
            tl_info.get("interest_rate_pct", 13.5)
            if isinstance(tl_info, dict)
            else 13.5
        )
        tl_emi = self._calculate_emi(
            tl_limit, tl_tenure, Decimal(str(tl_rate)) / Decimal("100")
        )
        base_dscr_tl, stressed_dscr_tl, post_loan_dscr_tl = self._derive_offer_dscrs(
            cap_summary, tl_emi
        )

        offers.append(
            {
                "tier": "BALANCED",
                "currency": "INR",
                "amount": str(tl_limit),
                "product_type": "TERM_LOAN",
                "tenure_months": tl_tenure,
                "interest_rate_pct": float(tl_rate),
                "repayment_frequency": "MONTHLY",
                "estimated_repayment": str(tl_emi),
                "base_dscr": base_dscr_tl,
                "stressed_dscr": stressed_dscr_tl,
                "post_loan_dscr": post_loan_dscr_tl,
                "collateral_structure": "Hypothecation of Plant & Machinery / CGTMSE Guarantee Coverage",
                "covenants": [
                    "Quarterly DSCR maintenance >= 1.25",
                    "Monthly Account Aggregator sync",
                    "No additional long-term indebtedness without prior bank consent",
                ],
                "evidence_checklist": [
                    "12-month Bank Statement Account Feed",
                    "Audited Financial Statements (3 years)",
                    "Verified Commercial CIBIL Report",
                ],
                "liquidity_impact": "MEDIUM",
                "applicable_capacity_ceilings": [str(tl_limit)],
                "binding_ceiling": str(tl_limit),
                "conditions": [
                    "Monthly AA sync",
                    "Quarterly GST submission",
                    f"Product rate: {tl_rate}% p.a.",
                ],
                "evidence_references": common_evidence_refs,
                "policy_version": POLICY_VERSION,
                "calculation_version": CALCULATION_VERSION,
                "human_review_required": True,
            }
        )

        # 3. INVOICE_DISCOUNTING / RECEIVABLES_FINANCE
        rf_info = product_limits.get("RECEIVABLES_FINANCE", {})
        rf_limit = (
            Decimal(str(rf_info.get("calculated_limit", "0.00")))
            if isinstance(rf_info, dict)
            else Decimal("0.00")
        )
        if rf_limit <= 0 or (
            isinstance(rf_info, dict)
            and rf_info.get("applicability") == "NOT_APPLICABLE"
        ):
            rf_limit = Decimal("0.00")
        elif max_borrowing_dec > 0 and rf_limit > max_borrowing_dec:
            rf_limit = max_borrowing_dec.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        rf_tenure = (
            rf_info.get("tenure_months", 12) if isinstance(rf_info, dict) else 12
        )
        rf_rate = (
            rf_info.get("interest_rate_pct", 11.0)
            if isinstance(rf_info, dict)
            else 11.0
        )
        rf_emi = self._calculate_emi(
            rf_limit, rf_tenure, Decimal(str(rf_rate)) / Decimal("100")
        )
        base_dscr_rf, stressed_dscr_rf, post_loan_dscr_rf = self._derive_offer_dscrs(
            cap_summary, rf_emi
        )

        offers.append(
            {
                "tier": "GROWTH",
                "currency": "INR",
                "amount": str(rf_limit),
                "product_type": "INVOICE_DISCOUNTING",
                "tenure_months": rf_tenure,
                "interest_rate_pct": float(rf_rate),
                "repayment_frequency": "ON_INVOICE_MATURITY",
                "estimated_repayment": str(rf_emi),
                "base_dscr": base_dscr_rf,
                "stressed_dscr": stressed_dscr_rf,
                "post_loan_dscr": post_loan_dscr_rf,
                "collateral_structure": "Assignment of receivables / Tri-party agreement with corporate anchor buyer",
                "covenants": [
                    "Invoices must be verified on e-Invoicing/GST portal",
                    "Max credit period 90 days",
                    "Direct escrow routing of invoice settlement proceeds",
                ],
                "evidence_checklist": [
                    "e-Invoice / GST Portal API integration feed",
                    "Anchor corporate buyer master agreement & purchase orders",
                    "12-month Bank Statement showing past invoice realization track",
                ],
                "liquidity_impact": "HIGH",
                "applicable_capacity_ceilings": [str(rf_limit)],
                "binding_ceiling": str(rf_limit),
                "conditions": [
                    "Monthly AA sync",
                    "Monthly GST submission",
                    "Escrow routing required",
                    f"Product rate: {rf_rate}% p.a.",
                ],
                "evidence_references": common_evidence_refs,
                "policy_version": POLICY_VERSION,
                "calculation_version": CALCULATION_VERSION,
                "human_review_required": True,
            }
        )

        return offers
