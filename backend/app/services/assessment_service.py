import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..db.orm.cases import Case, AssessmentSnapshot
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from ..schemas.responses import (
    AssessmentResultResponse,
    EvidencePassportResponse,
    CanonicalFeatureSnapshotResponse,
    FinancialHealthPillarResponse,
    AssessmentRangeResponse,
    ProductCapacityResponse,
    BindingConstraintResponse,
    StressScenarioResponse,
    BankabilityInterventionResponse,
    CovenantResponse,
)


class AssessmentService:
    @staticmethod
    def _utc_now():
        return datetime.now(timezone.utc)

    @classmethod
    def evaluate_case(cls, db: Session, case: Case) -> AssessmentResultResponse:
        """
        Derives features, computes scores, makes a decision, and generates an AssessmentResultResponse.
        It also persists the AssessmentSnapshot.
        Note: The case version MUST be updated (e.g., via cas_update_case_and_audit)
        BEFORE or ALONG WITH calling this, or the caller should be aware of the version.
        Actually, we can use the current case version and rely on the caller to update case first,
        or just use case.version.
        """
        # 1. Derive Features
        feature_engine = FeatureEngine(db, str(case.business_id_fk))
        features = feature_engine.derive_all_features()
        if case.monthly_revenue_inr is not None:
            features["monthly_revenue_inr"] = str(case.monthly_revenue_inr)

        # 2. Score
        scorer = ScoringEngine(features)
        scores = scorer.compute_all_scores()

        # 3. Decision
        req_product_str = (
            case.requested_product.value
            if hasattr(case.requested_product, "value")
            else str(case.requested_product)
        )
        policy = DecisionPolicy(
            features,
            scores,
            Decimal(str(case.requested_amount)),
            req_product_str,
        )
        decision = policy.evaluate()
        from app.domain.financial.engine import FinancialCapacityEngine

        cap = FinancialCapacityEngine.compute_capacity_from_features(
            features,
            Decimal(str(case.requested_amount)),
            req_product_str,
        )

        # 4. Build Canonical Assessment
        assessment = cls.build_assessment_result(case, features, scores, decision, cap)

        # 5. Persist Snapshot
        snapshot = AssessmentSnapshot(
            assessment_id=assessment.assessment_id,
            case_id=case.id,
            case_version=case.version,
            generated_at=assessment.generated_at,
            feature_snapshot=features,
            canonical_assessment_json=assessment.model_dump(mode="json"),
            engine_versions={
                "scoring": assessment.scoring_version,
                "calculation": assessment.calculation_version,
                "policy": assessment.policy_version,
                "feature": assessment.feature_schema_version,
            },
            evidence_ids=[str(e) for e in assessment.evidence_ids],
        )
        db.add(snapshot)
        db.flush()  # Ensure we hit uniqueness constraints if any

        return assessment

    @classmethod
    def build_assessment_result(
        cls,
        case: Case,
        features: dict,
        scores: dict,
        decision: dict,
        cap: Optional[dict] = None,
    ) -> AssessmentResultResponse:
        now = cls._utc_now()
        req_product_str = (
            case.requested_product.value
            if hasattr(case.requested_product, "value")
            else str(case.requested_product)
        )
        if cap is None:
            try:
                from app.domain.financial.engine import FinancialCapacityEngine

                cap = FinancialCapacityEngine.compute_capacity_from_features(
                    features,
                    Decimal(str(case.requested_amount)),
                    req_product_str,
                )
            except Exception:
                cap = {}

        try:
            from app.core.decision.limits import SafeLimitEngine

            limit_bridge = SafeLimitEngine.build_limit_bridge(
                features, req_product_str, Decimal(str(case.requested_amount))
            )
        except Exception:
            limit_bridge = None

        dscr_val = cap.get("current_dscr")
        if dscr_val is not None:
            dscr_val = Decimal(str(dscr_val))
        elif "bank_metrics" in features and "dscr" in features["bank_metrics"]:
            dscr_val = (
                Decimal(str(features["bank_metrics"]["dscr"]))
                if features["bank_metrics"]["dscr"] is not None
                else None
            )

        existing_ds_val = cap.get(
            "verified_existing_debt_service_monthly", Decimal("0.00")
        )
        existing_ds = (
            Decimal(str(existing_ds_val))
            if existing_ds_val is not None
            else Decimal("0.00")
        )

        proposed_emi_val = cap.get("proposed_emi")
        proposed_emi = (
            Decimal(str(proposed_emi_val)) if proposed_emi_val is not None else None
        )

        proposed_ds = existing_ds + (
            proposed_emi if proposed_emi is not None else Decimal("0.00")
        )

        post_loan_dscr_val = cap.get("post_loan_dscr")
        post_loan_dscr = (
            Decimal(str(post_loan_dscr_val))
            if post_loan_dscr_val is not None
            else (dscr_val * Decimal("0.9") if dscr_val else None)
        )

        stressed_dscr_val = cap.get("stressed_dscr")
        stressed_dscr = (
            Decimal(str(stressed_dscr_val)) if stressed_dscr_val is not None else None
        )

        req_amount = Decimal(str(case.requested_amount))

        # Build pillars (mocked / mapped from actual features if available)
        pillars = [
            FinancialHealthPillarResponse(**p) if isinstance(p, dict) else p
            for p in scores.get("six_pillars", [])
        ]
        if not pillars and "fhi_breakdown" in scores:
            for p_name, p_data in scores["fhi_breakdown"].items():
                s = p_data.get("score")
                if s is None:
                    h_stat = "MISSING_DATA"
                elif s >= 80:
                    h_stat = "STRONG"
                elif s >= 60:
                    h_stat = "ADEQUATE"
                elif s >= 40:
                    h_stat = "NEEDS_IMPROVEMENT"
                else:
                    h_stat = "WEAK"
                pillars.append(
                    FinancialHealthPillarResponse(
                        name=p_name.replace("_", " ").title(),
                        score=int(s) if s is not None else 0,
                        health_status=h_stat,
                        positive_reason_codes=p_data.get("positive_reason_codes", []),
                        adverse_reason_codes=p_data.get("adverse_reason_codes", []),
                        evidence_ids=p_data.get("evidence_ids", []),
                    )
                )

        # Extract limits
        max_amt = decision.get("binding_limit")
        if max_amt is None:
            max_amt = Decimal("0")
        else:
            max_amt = Decimal(str(max_amt))

        min_amt = req_amount * Decimal("0.5")
        if scores.get("score_range") and isinstance(scores["score_range"], dict):
            if scores["score_range"].get("min_amount") is not None:
                min_amt = Decimal(str(scores["score_range"]["min_amount"]))
            if scores["score_range"].get("max_amount") is not None:
                max_amt = Decimal(str(scores["score_range"]["max_amount"]))

        reasons_list = decision.get("reasons") or decision.get("reason_codes") or []
        binding_constraint = None
        if reasons_list:
            binding_constraint = BindingConstraintResponse(
                constraint_type="POLICY_RULE", reason=reasons_list[0]
            )

        top_covenants: list[CovenantResponse] = []
        for o in decision.get("offers", []):
            if isinstance(o, dict) and o.get("covenants"):
                for c_text in o["covenants"]:
                    if c_text not in [tc.covenant_text for tc in top_covenants]:
                        top_covenants.append(CovenantResponse(covenant_text=c_text))

        fhi_val = scores.get("financial_health_index")
        fhi = Decimal(str(fhi_val)) if fhi_val is not None else None

        credit_val = scores.get("vyapar_credit_health_score")
        credit_score = int(credit_val) if credit_val is not None else None

        # Evidence Tiers
        has_bank = (
            "bank_metrics" in features
            and features["bank_metrics"].get("months_filed", 0) > 0
        )
        has_gst = (
            "gst_metrics" in features
            and features["gst_metrics"].get("months_filed", 0) > 0
        )
        has_inv = (
            "invoice_metrics" in features
            and features["invoice_metrics"].get("total_invoices", 0) > 0
        )

        if has_bank and has_gst and has_inv:
            tier = "T3"
            tier_desc = "Gold Standard: Bank, GST, and Invoices all present."
        elif has_bank and has_gst:
            tier = "T2"
            tier_desc = "Strong: Bank and GST present."
        elif has_bank:
            tier = "T1"
            tier_desc = "Standard: Bank only."
        else:
            tier = "T0"
            tier_desc = "Insufficient: Missing Bank statements."

        ep_dict = {"evidence_tier": tier, "tier_description": tier_desc}

        return AssessmentResultResponse(
            assessment_id=uuid.uuid4(),
            case_id=case.id,
            case_version=case.version,
            generated_at=now,
            consent_state="VERIFIED",
            evidence_passport=EvidencePassportResponse(**ep_dict),
            feature_snapshot=CanonicalFeatureSnapshotResponse(**features),
            financial_health_index=fhi,
            six_pillars=pillars,
            vyapar_credit_health_score=credit_score,
            assessment_range=AssessmentRangeResponse(
                min_amount=min_amt, max_amount=max_amt
            ),
            evidence_certainty=str(scores.get("assessment_certainty", "HIGH")),
            integrity_state=str(features.get("integrity_state", "INTACT")),
            current_dscr=dscr_val,
            existing_debt_service=existing_ds,
            proposed_debt_service=proposed_ds,
            proposed_emi=proposed_emi,
            post_loan_dscr=post_loan_dscr,
            stressed_dscr=stressed_dscr,
            requested_product=req_product_str,
            requested_amount=req_amount,
            product_capacities=[
                ProductCapacityResponse(product_name="Term Loan", capacity=max_amt)
            ],
            selected_product=req_product_str,
            supportable_amount=max_amt,
            binding_constraint=binding_constraint,
            stress_results=cap.get(
                "stress_results",
                [
                    StressScenarioResponse(
                        scenario_name="NOT_AVAILABLE", impact="REQUIRED_INPUTS_MISSING"
                    )
                ],
            ),
            bankability_interventions=cap.get(
                "bankability_interventions",
                [
                    BankabilityInterventionResponse(
                        intervention_type="NOT_AVAILABLE",
                        description="REQUIRED_INPUTS_MISSING",
                    )
                ],
            ),
            policy_recommendation=decision.get("decision", "DECLINE_RECOMMENDED"),
            policy_reason_codes=reasons_list,
            offers=decision.get("offers", []),
            conditions=decision.get("conditions", []),
            covenants=top_covenants,
            analyst_recommendation=case.analyst_recommendation.value
            if case.analyst_recommendation
            else None,
            analyst_reason=None,
            human_decision=case.human_decision.value if case.human_decision else None,
            approved_amount=None,
            scoring_version="2.0",
            calculation_version="1.5",
            policy_version="2026.Q2",
            passport_version="1.0",
            feature_schema_version="3.1",
            evidence_ids=[],
            limitations=[],
            limit_bridge=limit_bridge,
        )

    @classmethod
    def get_latest_assessment(
        cls, db: Session, case_id: Union[uuid.UUID, str]
    ) -> Optional[AssessmentResultResponse]:
        snap = (
            db.query(AssessmentSnapshot)
            .filter(AssessmentSnapshot.case_id == case_id)
            .order_by(desc(AssessmentSnapshot.case_version))
            .first()
        )
        if not snap:
            return None
        # Convert dict to model
        # Rehydrate UUID strings to objects if necessary, but model_validate should handle it
        return AssessmentResultResponse.model_validate(snap.canonical_assessment_json)

    @classmethod
    def get_assessment_by_id(
        cls, db: Session, assessment_id: Union[uuid.UUID, str]
    ) -> Optional[AssessmentResultResponse]:
        snap = (
            db.query(AssessmentSnapshot)
            .filter(AssessmentSnapshot.assessment_id == assessment_id)
            .first()
        )
        if not snap:
            return None
        return AssessmentResultResponse.model_validate(snap.canonical_assessment_json)
