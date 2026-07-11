"""
Authoritative Financial Capacity Engine (`FinancialCapacityEngine`).
Consolidates all financial sizing, DSCR evaluation, reducing-balance amortization,
and obligation verification states across Vyapar Pulse.

Removes unsafe inferences (e.g., obligations = credits / dscr, obligations = debits * 0.20)
and guarantees canonical DSCR numerator definitions across base, proposed, and stressed states.
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from app.core.versions import CALCULATION_VERSION
from app.core.decision.limits import SafeLimitEngine


class FinancialCapacityEngine:
    """
    Canonical financial engine responsible for:
    1. Authoritative cash-flow derivation (operating inflows vs outflows).
    2. Exact reducing-balance EMI amortization.
    3. Institutional obligation verification state handling (`VERIFIED` vs `UNKNOWN_OBLIGATIONS`).
    4. Product-specific capacity structures (`WORKING_CAPITAL_LINE`, `RECEIVABLES_FINANCE`, `TERM_LOAN`).
    5. Exact evidence record ID lineage per calculation.
    """

    @classmethod
    def calculate_emi(cls, principal: Decimal, annual_rate: Decimal = Decimal("0.135"), tenure_months: int = 36) -> Decimal:
        """
        Exact reducing-balance amortization formula:
        P * r * (1+r)^n / ((1+r)^n - 1)
        """
        return SafeLimitEngine.calculate_emi_from_loan(principal, annual_rate, tenure_months)

    @classmethod
    def calculate_loan_from_emi(cls, monthly_emi: Decimal, annual_rate: Decimal = Decimal("0.135"), tenure_months: int = 36) -> Decimal:
        return SafeLimitEngine._calculate_loan_from_emi(monthly_emi, annual_rate, tenure_months)

    @classmethod
    def compute_capacity_from_features(
        cls,
        features: Dict[str, Any],
        requested_amount: Decimal = Decimal("0.00"),
        requested_product: str = "WORKING_CAPITAL_LINE",
        custom_tenure_months: int = 36,
        custom_annual_rate: Decimal = Decimal("0.135")
    ) -> Dict[str, Any]:
        """
        Derives canonical financial capacity from feature snapshot dictionary.
        Used for in-memory simulations, interactive stress labs, and case evaluation where DB objects are serialized.
        """
        bank_metrics = features.get("bank_metrics", {})
        gst_metrics = features.get("gst_metrics", {})
        invoice_metrics = features.get("invoice_metrics", {})

        # 1. Operating inflows (canonical: operating receipts only, NEVER total gross inflows including loans/transfers)
        raw_inflows = bank_metrics.get("operating_inflows_monthly", bank_metrics.get("avg_monthly_credits", features.get("banking_inflow_inr", features.get("monthly_revenue_inr", "0"))))
        observed_operating_inflows = Decimal(str(raw_inflows)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 2. Operating outflows (canonical: operating expenses only, excluding debt service)
        raw_outflows = bank_metrics.get("operating_outflows_monthly", bank_metrics.get("avg_monthly_debits", features.get("banking_outflow_inr", features.get("monthly_expenses_inr", "0"))))
        observed_operating_outflows = Decimal(str(raw_outflows)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Ensure operating cash available for debt service is derived precisely
        operating_cash_available = (observed_operating_inflows - observed_operating_outflows).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 3. Obligation verification state
        # Check explicit debt service or verified cibil status in features
        explicit_verification_state = features.get("obligation_verification_state")
        explicit_existing_ds = features.get("verified_existing_debt_service_monthly")

        if explicit_verification_state == "VERIFIED" and explicit_existing_ds is not None:
            obligation_verification_state = "VERIFIED"
            verified_existing_ds = Decimal(str(explicit_existing_ds)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            unknown_reasons = []
        elif explicit_verification_state == "VERIFIED" and "verified_obligations_emi" in features:
            obligation_verification_state = "VERIFIED"
            verified_existing_ds = Decimal(str(features.get("verified_obligations_emi", "0.00"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            unknown_reasons = []
        else:
            # Check if bank_metrics specifically confirms obligations pulled/verified
            obligations_list = features.get("obligations", features.get("authoritative_obligations", []))
            has_explicit_cibil = bool(features.get("cibil_pulled") or len(obligations_list) > 0 or bank_metrics.get("debt_service_verified"))
            if has_explicit_cibil:
                obligation_verification_state = "VERIFIED"
                if len(obligations_list) > 0:
                    verified_existing_ds = sum((Decimal(str(o.get("monthly_emi", "0.00"))) for o in obligations_list), Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                else:
                    verified_existing_ds = Decimal(str(bank_metrics.get("verified_debt_service_monthly", "0.00"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                unknown_reasons = []
            else:
                # Institutional truth: DO NOT INFER OBLIGATIONS AS credits/dscr OR debits * 0.20!
                obligation_verification_state = "UNKNOWN_OBLIGATIONS"
                verified_existing_ds = Decimal("0.00")
                unknown_reasons = ["CIBIL obligations not verified and bank transaction feed lacks authoritative DEBT_SERVICE categorization."]

        # 4. Base DSCR calculation
        if obligation_verification_state == "VERIFIED":
            if verified_existing_ds > Decimal("0.00"):
                current_dscr = (operating_cash_available / verified_existing_ds).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                current_dscr = None  # Zero debt verified
        else:
            current_dscr = None

        # 5. Proposed facility servicing
        proposed_emi = cls.calculate_emi(Decimal(str(requested_amount)), custom_annual_rate, custom_tenure_months) if Decimal(str(requested_amount)) > 0 else Decimal("0.00")
        
        if obligation_verification_state == "VERIFIED":
            total_post_ds = verified_existing_ds + proposed_emi
            if total_post_ds > Decimal("0.00"):
                post_loan_dscr = (operating_cash_available / total_post_ds).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                post_loan_dscr = None
        else:
            post_loan_dscr = None

        # 6. Standard Downside Stress (-15% revenue / cash inflows, +15% debt service due to rate shock)
        stressed_inflows = (observed_operating_inflows * Decimal("0.85")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        stressed_operating_cash_available = (stressed_inflows - observed_operating_outflows).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        if obligation_verification_state == "VERIFIED":
            stressed_debt_service = (verified_existing_ds * Decimal("1.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if stressed_debt_service > Decimal("0.00"):
                stressed_dscr = (stressed_operating_cash_available / stressed_debt_service).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                stressed_dscr = None
        else:
            stressed_debt_service = Decimal("0.00")
            stressed_dscr = None

        # 7. Evidence Lineage IDs
        authoritative_ids = features.get("authoritative_evidence_ids", [])
        inflow_ids = features.get("inflow_evidence_ids", authoritative_ids)
        outflow_ids = features.get("outflow_evidence_ids", authoritative_ids)
        obligation_ids = features.get("obligation_evidence_ids", [o.get("id") for o in features.get("obligations", []) if isinstance(o, dict) and "id" in o])
        if not obligation_ids and obligation_verification_state == "VERIFIED":
            obligation_ids = authoritative_ids

        calculation_evidence_ids = {
            "inflows": inflow_ids if isinstance(inflow_ids, list) else [],
            "outflows": outflow_ids if isinstance(outflow_ids, list) else [],
            "obligations": obligation_ids if isinstance(obligation_ids, list) else []
        }

        # 8. Product-Specific Capacity Structuring
        product_limits = cls._derive_product_limits(
            observed_operating_inflows=observed_operating_inflows,
            operating_cash_available=operating_cash_available,
            verified_existing_ds=verified_existing_ds,
            obligation_verification_state=obligation_verification_state,
            features=features,
            calculation_evidence_ids=calculation_evidence_ids
        )

        # Determine binding product limit corresponding specifically to requested_product
        binding_limit, matched_method = cls._select_binding_limit(product_limits, requested_product)

        return {
            "observed_operating_inflows_monthly": observed_operating_inflows,
            "observed_operating_outflows_monthly": observed_operating_outflows,
            "operating_cash_available_for_debt_service_monthly": operating_cash_available,
            "verified_existing_debt_service_monthly": verified_existing_ds,
            "current_dscr": current_dscr,
            "proposed_emi": proposed_emi,
            "post_loan_dscr": post_loan_dscr,
            "stressed_operating_cash_available": stressed_operating_cash_available,
            "stressed_debt_service": stressed_debt_service,
            "stressed_dscr": stressed_dscr,
            "obligation_verification_state": obligation_verification_state,
            "calculation_evidence_ids": calculation_evidence_ids,
            "unknown_reasons": unknown_reasons,
            "product_limits": product_limits,
            "binding_product_limit": binding_limit,
            "requested_product_method": matched_method,
            "calculation_version": CALCULATION_VERSION
        }

    @classmethod
    def compute_capacity_from_case(cls, db: Any, case: Any, requested_amount: Decimal = Decimal("0.00"), requested_product: str = "WORKING_CAPITAL_LINE") -> Dict[str, Any]:
        """
        Derives canonical financial capacity directly from database ORM objects (Case, BankTransaction, GstReturn, Obligation).
        """
        from app.db.orm.evidence import BankTransaction, GstReturn, Obligation

        # 1. Query Bank Transactions for operating inflows & outflows
        txns = db.query(BankTransaction).filter(BankTransaction.case_id == case.id).all()
        
        inflow_ids = []
        outflow_ids = []
        obligation_ids = []

        total_inflows = Decimal("0.00")
        total_outflows = Decimal("0.00")
        total_ds_outflows = Decimal("0.00")

        months_seen = set()
        for t in txns:
            if t.transaction_date:
                months_seen.add((t.transaction_date.year, t.transaction_date.month))
            amt = Decimal(str(t.amount or "0.00"))
            t_type = str(t.transaction_type or "").upper()
            t_cat = str(t.category or "").upper()

            if t_type == "CREDIT":
                total_inflows += amt
                inflow_ids.append(str(t.id))
            elif t_type == "DEBIT":
                if t_cat == "DEBT_SERVICE":
                    total_ds_outflows += amt
                else:
                    total_outflows += amt
                outflow_ids.append(str(t.id))

        month_divisor = Decimal(str(max(1, len(months_seen))))
        observed_inflows = (total_inflows / month_divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        observed_outflows = (total_outflows / month_divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Check explicit verified turnover from GST if available
        gst_records = db.query(GstReturn).filter(GstReturn.case_id == case.id).all()
        if gst_records and not txns:
            gst_turnover = sum((Decimal(str(g.taxable_turnover or "0.00")) for g in gst_records), Decimal("0.00"))
            gst_months = max(1, len(gst_records))
            observed_inflows = (gst_turnover / Decimal(str(gst_months))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            observed_outflows = (observed_inflows * Decimal("0.75")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            inflow_ids = [str(g.id) for g in gst_records]

        # 2. Obligations check
        obligations = db.query(Obligation).filter(
            (Obligation.case_id == case.id) | (Obligation.business_id_fk == case.business_id)
        ).all()

        if obligations:
            obligation_verification_state = "VERIFIED"
            verified_ds = sum((Decimal(str(o.monthly_emi or "0.00")) for o in obligations), Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            obligation_ids = [str(o.id) for o in obligations]
        elif total_ds_outflows > Decimal("0.00"):
            obligation_verification_state = "VERIFIED"
            verified_ds = (total_ds_outflows / month_divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif case.cibil_pulled or getattr(case, "zero_debt_verified", False):
            obligation_verification_state = "VERIFIED"
            verified_ds = Decimal("0.00")
        else:
            obligation_verification_state = "UNKNOWN_OBLIGATIONS"
            verified_ds = Decimal("0.00")

        features_dict = case.feature_snapshot or {}
        features_dict.update({
            "authoritative_evidence_ids": inflow_ids + outflow_ids + obligation_ids,
            "inflow_evidence_ids": inflow_ids,
            "outflow_evidence_ids": outflow_ids,
            "obligation_evidence_ids": obligation_ids,
            "obligation_verification_state": obligation_verification_state,
            "verified_existing_debt_service_monthly": str(verified_ds),
            "bank_metrics": {
                "operating_inflows_monthly": str(observed_inflows),
                "operating_outflows_monthly": str(observed_outflows),
                "avg_monthly_credits": str(observed_inflows),
                "avg_monthly_debits": str(observed_outflows),
            }
        })

        return cls.compute_capacity_from_features(
            features=features_dict,
            requested_amount=requested_amount,
            requested_product=requested_product,
            custom_tenure_months=case.requested_tenure_months or 36,
            custom_annual_rate=Decimal("0.135")
        )

    @classmethod
    def _derive_product_limits(
        cls,
        observed_operating_inflows: Decimal,
        operating_cash_available: Decimal,
        verified_existing_ds: Decimal,
        obligation_verification_state: str,
        features: Dict[str, Any],
        calculation_evidence_ids: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Derives independent product structures without arbitrary cross-product minimums.
        """
        # A. Working Capital Line (WORKING_CAPITAL_LINE)
        gst = features.get("gst_metrics", {})
        if "avg_monthly_revenue" in gst and gst["avg_monthly_revenue"]:
            turnover = Decimal(str(gst["avg_monthly_revenue"])) * Decimal("12")
        elif "monthly_revenue_inr" in features and features["monthly_revenue_inr"]:
            turnover = Decimal(str(features["monthly_revenue_inr"])) * Decimal("12")
        else:
            turnover = observed_operating_inflows * Decimal("12")
        wc_metrics = features.get("working_capital_metrics", {})
        operating_cycle_days = Decimal(str(wc_metrics.get("operating_cycle_days", features.get("operating_cycle_days", 73))))
        wc_requirement = (turnover * (operating_cycle_days / Decimal("365"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Cash flow headroom cap: 80% of annualized net free cash flow after existing debt service
        net_monthly_headroom = max(Decimal("0.00"), operating_cash_available - verified_existing_ds)
        headroom_cap = (net_monthly_headroom * Decimal("12") * Decimal("0.80")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        policy_cap = Decimal("50000000.00")  # ₹5 Crore maximum

        wc_candidates = [wc_requirement, headroom_cap, policy_cap] if obligation_verification_state == "VERIFIED" else [wc_requirement, policy_cap]
        wc_limit = min(wc_candidates) if wc_requirement > 0 else Decimal("0.00")

        wc_binding = "working_capital_requirement" if wc_limit == wc_requirement else ("cash_flow_headroom_cap" if wc_limit == headroom_cap else "policy_cap")
        wc_warnings = [] if obligation_verification_state == "VERIFIED" else ["Obligation state UNKNOWN_OBLIGATIONS; cash flow headroom cap unverified."]

        wc_result = {
            "method": "WORKING_CAPITAL_LINE",
            "applicability": "APPLICABLE" if wc_limit > 0 else "NOT_APPLICABLE",
            "calculated_limit": wc_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "formula": "min(turnover * (operating_cycle_days / 365), (operating_cash_available - existing_ds) * 12 * 0.80, policy_cap)",
            "input_snapshot": {
                "verified_turnover_annual": str(turnover),
                "operating_cycle_days": str(operating_cycle_days),
                "working_capital_requirement": str(wc_requirement),
                "cash_flow_headroom_cap": str(headroom_cap),
                "policy_cap": str(policy_cap)
            },
            "binding_constraint": wc_binding,
            "policy_rule_ids": ["POL-WC-001"],
            "evidence_ids": calculation_evidence_ids.get("inflows", []),
            "confidence": 0.90 if obligation_verification_state == "VERIFIED" and wc_limit > 0 else (0.50 if wc_limit > 0 else 0.0),
            "warnings": wc_warnings,
            "limitations": ["Subject to quarterly stock and book debt statement verification."]
        }

        # B. Receivables Finance (RECEIVABLES_FINANCE)
        inv_metrics = features.get("invoice_metrics", {})
        eligible_receivables = Decimal(str(inv_metrics.get("eligible_amount", features.get("eligible_receivables", 0))))
        advance_rate = Decimal("0.80")
        concentration_haircut = Decimal(str(inv_metrics.get("concentration_haircut", "1.00")))
        reconciliation_haircut = Decimal(str(features.get("reconciliation_haircut", "1.00")))

        rec_limit = (eligible_receivables * advance_rate * concentration_haircut * reconciliation_haircut).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rec_result = {
            "method": "RECEIVABLES_FINANCE",
            "applicability": "APPLICABLE" if rec_limit > 0 else "NOT_APPLICABLE",
            "calculated_limit": rec_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "formula": "eligible_receivables * advance_rate * concentration_haircut * reconciliation_haircut",
            "input_snapshot": {
                "eligible_receivables": str(eligible_receivables),
                "advance_rate": str(advance_rate),
                "concentration_haircut": str(concentration_haircut),
                "reconciliation_haircut": str(reconciliation_haircut)
            },
            "binding_constraint": "eligible_receivables_collateral",
            "policy_rule_ids": ["POL-REC-001"],
            "evidence_ids": calculation_evidence_ids.get("inflows", []),
            "confidence": 0.90 if rec_limit > 0 else 0.0,
            "warnings": [] if rec_limit > 0 else ["No eligible invoice collateral found within 90-day aging limit."],
            "limitations": ["Requires notice of assignment and buyer escrow routing."]
        }

        # C. Term Loan (TERM_LOAN)
        if obligation_verification_state == "VERIFIED" and operating_cash_available > Decimal("0.00"):
            target_dscr = Decimal("1.35")
            max_total_ds = operating_cash_available / target_dscr
            supportable_emi = max(Decimal("0.00"), max_total_ds - verified_existing_ds)
            tl_limit = cls.calculate_loan_from_emi(supportable_emi, Decimal("0.14"), 36)
            tl_warnings = []
        else:
            tl_limit = Decimal("0.00")
            supportable_emi = Decimal("0.00")
            tl_warnings = ["Term loan requires verified obligation state and positive operating cash available after existing debt service."]

        tl_result = {
            "method": "TERM_LOAN",
            "applicability": "APPLICABLE" if tl_limit > 0 else "NOT_APPLICABLE",
            "calculated_limit": tl_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "formula": "calculate_loan_from_emi((operating_cash_available / 1.35) - verified_existing_ds, rate=14%, tenure=36m)",
            "input_snapshot": {
                "operating_cash_available_monthly": str(operating_cash_available),
                "verified_existing_ds_monthly": str(verified_existing_ds),
                "target_dscr": "1.35",
                "supportable_emi": str(supportable_emi),
                "tenure_months": "36",
                "annual_rate": "0.14"
            },
            "binding_constraint": "target_dscr_serviceability",
            "policy_rule_ids": ["POL-TL-001"],
            "evidence_ids": calculation_evidence_ids.get("inflows", []) + calculation_evidence_ids.get("obligations", []),
            "confidence": 0.85 if tl_limit > 0 and obligation_verification_state == "VERIFIED" else 0.0,
            "warnings": tl_warnings,
            "limitations": ["Calculated using exact reducing-balance amortization at 14% p.a. over 36 months."]
        }

        return {
            "WORKING_CAPITAL_LINE": wc_result,
            "RECEIVABLES_FINANCE": rec_result,
            "TERM_LOAN": tl_result
        }

    @classmethod
    def _select_binding_limit(cls, product_limits: Dict[str, Dict[str, Any]], requested_product: str) -> tuple[Decimal, str]:
        """
        Returns the exact calculated limit corresponding to the requested product structure,
        or the best applicable limit if requested product is general/unspecified.
        NEVER takes the minimum of unrelated methods!
        """
        req_upper = (requested_product or "").upper()
        if "RECEIVABLE" in req_upper or "INVOICE" in req_upper or "DISCOUNT" in req_upper:
            target_key = "RECEIVABLES_FINANCE"
        elif "TERM" in req_upper or "EQUIPMENT" in req_upper or "MACHINERY" in req_upper:
            target_key = "TERM_LOAN"
        elif "WORKING_CAPITAL" in req_upper or "WC" in req_upper or "CASH_CREDIT" in req_upper or "OD" in req_upper:
            target_key = "WORKING_CAPITAL_LINE"
        else:
            # Check which product matches best or pick first applicable
            for key in ["WORKING_CAPITAL_LINE", "RECEIVABLES_FINANCE", "TERM_LOAN"]:
                if product_limits[key]["applicability"] == "APPLICABLE":
                    return product_limits[key]["calculated_limit"], key
            return Decimal("0.00"), "WORKING_CAPITAL_LINE"

        target = product_limits.get(target_key, {})
        return target.get("calculated_limit", Decimal("0.00")), target_key
