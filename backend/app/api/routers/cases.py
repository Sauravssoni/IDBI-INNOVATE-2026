from app.schemas.responses import (
    CaseDetailResponse,
    DecisionPackageResponse,
    DecisionPackageReconciliation,
    DecisionPackageAuditItem,
)
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from uuid import UUID
import uuid
from typing import Optional, Any
from app.db.session import SessionLocal
from pydantic import BaseModel
from app.db.orm.cases import (
    Case,
    CaseStatus,
    HumanDecisionAction,
    AnalystRecommendationAction,
    AuditEvent,
    IdempotencyRecord,
    IdempotencyStatus,
    utc_now,
)
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.api.dependencies import get_current_user
from app.core.audit import calculate_audit_hash
from app.db.orm.users import User
from app.services.authz import (
    apply_case_list_scope,
    can_view_case,
    can_run_assessment,
    can_submit_analyst_recommendation,
    can_record_human_decision,
    can_view_audit,
)
import hashlib
import json
import datetime
from fastapi.encoders import jsonable_encoder
# Wrappers removed, using can_* directly


def check_can_view_audit(db: Session, case: Case, user: User) -> bool:
    try:
        can_view_audit(db, case, user)
        return True
    except HTTPException:
        return False


router = APIRouter(prefix="/api/cases", tags=["cases"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reserve_idempotency_key(
    db: Session, key: str, req_hash: str, user_id: str, case_id: str, action: str
):
    now = utc_now()
    expires = now + datetime.timedelta(days=1)

    if len(key) < 10 or len(key) > 100:
        raise HTTPException(status_code=400, detail="Invalid Idempotency-Key length")

    try:
        record = IdempotencyRecord(
            idempotency_key=key,
            user_id=user_id,
            case_id=case_id,
            action=action,
            request_hash=req_hash,
            status=IdempotencyStatus.IN_PROGRESS,
            expires_at=expires,
        )
        db.add(record)
        db.commit()
        return None, record.id
    except IntegrityError:
        db.rollback()

        existing_record = (
            db.query(IdempotencyRecord)
            .filter(
                IdempotencyRecord.idempotency_key == key,
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.case_id == case_id,
                IdempotencyRecord.action == action,
            )
            .first()
        )

        if not existing_record:
            raise HTTPException(
                status_code=500, detail="Idempotency conflict but record not found"
            )

        if existing_record.status == IdempotencyStatus.COMPLETED:
            if existing_record.request_hash != req_hash:
                raise HTTPException(
                    status_code=409, detail="Idempotency key mismatch with payload"
                )
            return existing_record.response_payload, existing_record.id

        if (
            existing_record.status == IdempotencyStatus.FAILED_RETRYABLE
            or existing_record.expires_at < now
        ):
            if existing_record.request_hash != req_hash:
                raise HTTPException(
                    status_code=409, detail="Idempotency key mismatch with payload"
                )
            existing_record.status = IdempotencyStatus.IN_PROGRESS
            # Preserve original request hash, do not replace it!
            existing_record.expires_at = expires
            existing_record.response_payload = None
            db.commit()
            return None, existing_record.id

        if existing_record.status == IdempotencyStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "IDEMPOTENCY_IN_PROGRESS",
                    "message": "An identical request is currently being processed.",
                    "retryable": True,
                    "retry_after_seconds": 5,
                },
                headers={"Retry-After": "5"},
            )

        raise HTTPException(status_code=500, detail="Unknown idempotency state")


def fulfill_idempotency(
    db: Session, record_id: uuid.UUID, status_code: int, payload: dict
):
    db.query(IdempotencyRecord).filter(IdempotencyRecord.id == record_id).update(
        {
            "status": IdempotencyStatus.COMPLETED,
            "response_status": status_code,
            "response_payload": payload,
        }
    )


def cas_update_case_and_audit(
    db: Session,
    case_id: UUID,
    expected_version: int,
    update_values: dict,
    user: User,
    action: str,
    reason: str,
    metadata: dict,
    idempotency_record_id: UUID,
):
    """
    Perform a Compare-And-Swap (CAS) update on the Case, append to AuditEvent, and fulfill idempotency atomically.
    """
    set_clause = ", ".join([f"{k} = :{k}" for k in update_values.keys()])
    params = update_values.copy()
    params["case_id"] = str(case_id)
    params["expected_version"] = expected_version

    update_stmt = text(f"""
        UPDATE cases
        SET {set_clause}, version = version + 1
        WHERE id = :case_id AND version = :expected_version
        RETURNING version
    """)  # nosec B608

    result = db.execute(update_stmt, params).fetchone()

    if not result:
        # Fetch current version to return in STALE_VERSION error
        current_case = db.query(Case.version).filter(Case.id == case_id).first()
        current_v = current_case.version if current_case else None

        # Mark as FAILED_RETRYABLE
        db.query(IdempotencyRecord).filter(
            IdempotencyRecord.id == idempotency_record_id
        ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
        db.commit()

        raise HTTPException(
            status_code=409,
            detail={
                "code": "STALE_VERSION",
                "current_version": current_v,
                "message": "The case has been modified by another request. Please retry with the latest version.",
                "retryable": True,
            },
        )

    resulting_version = result[0]
    prior_version = resulting_version - 1

    prev_event = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.event_sequence.desc())
        .first()
    )
    prior_hash = prev_event.event_hash if prev_event else "GENESIS"
    event_sequence = (prev_event.event_sequence + 1) if prev_event else 1

    metadata_enc = jsonable_encoder(metadata)
    correlation_id = str(uuid.uuid4())
    now_utc = utc_now()

    hash_payload = {
        "sequence": event_sequence,
        "actor": str(user.id),
        "actor_role": user.role.value,
        "action": action,
        "rationale": reason,
        "correlation_id": correlation_id,
        "prior_version": prior_version,
        "resulting_version": resulting_version,
        "idempotency_record_id": str(idempotency_record_id),
        "model_version": "1.0",
        "policy_version": "1.0",
        "timestamp": now_utc.isoformat(),
        "metadata": metadata_enc,
    }

    event_hash = calculate_audit_hash(prior_hash, hash_payload)

    audit = AuditEvent(
        case_id=case_id,
        event_sequence=event_sequence,
        event_type=action,
        actor=str(user.id),
        actor_role=user.role.value,
        idempotency_record_id=idempotency_record_id,
        prior_case_version=prior_version,
        resulting_case_version=resulting_version,
        reason=reason,
        correlation_id=correlation_id,
        model_version="1.0",
        policy_version="1.0",
        metadata_json=metadata_enc,
        prior_event_hash=prior_hash,
        event_hash=event_hash,
        created_at=now_utc,
    )
    db.add(audit)

    metadata["prior_version"] = prior_version
    metadata["resulting_version"] = resulting_version
    metadata["audit_hash"] = event_hash
    metadata_enc["prior_version"] = prior_version
    metadata_enc["resulting_version"] = resulting_version
    metadata_enc["audit_hash"] = event_hash

    fulfill_idempotency(db, idempotency_record_id, 200, metadata_enc)

    db.commit()


@router.get("/summary")
def get_cases_summary(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    now = utc_now()
    cases = apply_case_list_scope(db, db.query(Case), user, now).all()

    active_cases = len(cases)
    total_requested_amount = sum((c.requested_amount or Decimal(0)) for c in cases)

    awaiting_analyst = 0
    awaiting_human = 0
    approved_cases = 0
    approved_amount = Decimal(0)
    declined_cases = 0
    deferred_cases = 0
    completed_human_reviews = 0

    for c in cases:
        # Pending Analyst Review: ASSESSMENT_COMPLETED and no analyst recommendation
        if c.status == CaseStatus.ASSESSMENT_COMPLETED and not c.analyst_recommendation:
            awaiting_analyst += 1
        # Pending Assessment: INITIATED or EVIDENCE_GATHERING
        elif c.status in [CaseStatus.INITIATED, CaseStatus.EVIDENCE_GATHERING]:
            # This is Pending Assessment, but the API doesn't have a field for it,
            # wait, the API has awaiting_analyst and awaiting_human_decision.
            pass
        # Pending Sanction: DECISION_PENDING and no human decision
        elif c.status == CaseStatus.DECISION_PENDING and not c.human_decision:
            awaiting_human += 1

        if c.status in [
            CaseStatus.HUMAN_APPROVED,
            CaseStatus.HUMAN_DECLINED,
            CaseStatus.HUMAN_DEFERRED,
        ]:
            completed_human_reviews += 1
            if c.status == CaseStatus.HUMAN_APPROVED:
                approved_cases += 1
                latest_dec = (
                    db.query(AuditEvent)
                    .filter(
                        AuditEvent.case_id == c.id,
                        AuditEvent.event_type == "human_decision",
                    )
                    .order_by(AuditEvent.created_at.desc())
                    .first()
                )
                if (
                    latest_dec
                    and latest_dec.metadata_json
                    and "approved_amount" in latest_dec.metadata_json
                ):
                    approved_amount += Decimal(
                        str(latest_dec.metadata_json["approved_amount"])
                    )
                else:
                    approved_amount += c.requested_amount or Decimal(0)
            elif c.status == CaseStatus.HUMAN_DECLINED:
                declined_cases += 1
            elif c.status == CaseStatus.HUMAN_DEFERRED:
                deferred_cases += 1

    return {
        "active_cases": active_cases,
        "total_requested_amount": float(total_requested_amount),
        "awaiting_analyst": awaiting_analyst,
        "awaiting_human_decision": awaiting_human,
        "approved_cases": approved_cases,
        "approved_amount": float(approved_amount),
        "declined_cases": declined_cases,
        "deferred_cases": deferred_cases,
        "completed_human_reviews": completed_human_reviews,
    }


@router.get("")
@router.get("/")
def list_cases(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    now = utc_now()
    query = apply_case_list_scope(db, db.query(Case), user, now)
    cases = (
        query.order_by(Case.created_at.desc(), Case.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    results = []
    for c in cases:
        results.append(
            {
                "id": str(c.id),
                "business_id": str(c.business.business_id),
                "business_name": c.business.legal_name,
                "status": c.status.value,
                "requested_amount": c.requested_amount,
                "currency": c.currency,
                "created_at": c.created_at,
                "assigned_analyst": str(c.assigned_credit_analyst_id)
                if c.assigned_credit_analyst_id
                else "Unassigned",
                "assigned_rm": str(c.assigned_relationship_manager_id)
                if c.assigned_relationship_manager_id
                else "Unassigned",
                "requested_product": c.requested_product.value
                if c.requested_product
                else None,
                "recommendation": c.recommendation.value if c.recommendation else None,
                "analyst_recommendation": c.analyst_recommendation.value
                if c.analyst_recommendation
                else None,
                "human_decision": c.human_decision.value if c.human_decision else None,
            }
        )
    return results


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)

    latest_eval = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case.id, AuditEvent.event_type == "evaluate")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    evaluation_result = latest_eval.metadata_json if latest_eval else None

    return {
        "id": str(case.id),
        "business_id_fk": str(case.business_id_fk),
        "business": {
            "id": str(case.business.id),
            "business_id": case.business.business_id,
            "legal_name": case.business.legal_name,
            "sector": case.business.sector,
        },
        "requested_amount": case.requested_amount,
        "requested_product": case.requested_product.value
        if case.requested_product
        else None,
        "currency": case.currency,
        "status": case.status.value,
        "recommendation": case.recommendation.value if case.recommendation else None,
        "analyst_recommendation": case.analyst_recommendation.value
        if case.analyst_recommendation
        else None,
        "human_decision": case.human_decision.value if case.human_decision else None,
        "evaluation_result": evaluation_result,
        "allowed_actions": {
            "run_assessment": can_run_assessment(db, case, user).model_dump(),
            "submit_analyst_recommendation": can_submit_analyst_recommendation(
                db, case, user
            ).model_dump(),
            "record_human_decision": can_record_human_decision(
                db, case, user
            ).model_dump(),
            "view_audit": check_can_view_audit(db, case, user),
        },
        "version": case.version,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


class EvaluateCaseRequest(BaseModel):
    expected_version: int


@router.post("/{case_id}/evaluate")
def evaluate_case(
    case_id: UUID,
    req: EvaluateCaseRequest,
    fastapi_req: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = can_view_case(db, user, case_id)

    req_hash = hashlib.sha256(
        json.dumps(req.model_dump(), sort_keys=True, default=str).encode()
    ).hexdigest()

    cached, record_id = reserve_idempotency_key(
        db, idempotency_key, req_hash, str(user.id), str(case.id), "evaluate"
    )
    if cached is not None:
        return cached

    ctx = can_run_assessment(db, case, user)
    if not ctx.allowed:
        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(
            status_code=403,
            detail={"code": ctx.blocked_reason_code, "message": ctx.message},
        )

    try:
        # 1. Derive Features
        feature_engine = FeatureEngine(db, str(case.business_id_fk))
        features = feature_engine.derive_all_features()

        # 2. Score
        scorer = ScoringEngine(features)
        scores = scorer.compute_all_scores()

        # 3. Decision
        policy = DecisionPolicy(
            features,
            scores,
            Decimal(str(case.requested_amount)),
            case.requested_product.value,
        )
        decision = policy.evaluate()

        result_payload = {
            "case_id": str(case.id),
            "business_name": case.business.legal_name,
            "features": features,
            "scores": scores,
            "decision": decision,
        }

        dscr_val = None
        if (
            "bank_metrics" in features
            and "dscr" in features["bank_metrics"]
            and features["bank_metrics"]["dscr"] is not None
        ):
            dscr_val = Decimal(str(features["bank_metrics"]["dscr"]))

        update_values = {
            "recommendation": decision["decision"],
            "status": CaseStatus.ASSESSMENT_COMPLETED.value,
            "dscr": dscr_val,
        }

        cas_update_case_and_audit(
            db=db,
            case_id=case_id,
            expected_version=req.expected_version,
            update_values=update_values,
            user=user,
            action="evaluate",
            reason="System Evaluation",
            metadata=result_payload,
            idempotency_record_id=record_id,
        )

        return result_payload
    except HTTPException:
        raise
    except Exception:
        db.rollback()

        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(status_code=500, detail="Internal processing error")


class AnalystRecommendationRequest(BaseModel):
    recommendation: AnalystRecommendationAction
    reason: str
    expected_version: int


@router.post("/{case_id}/analyst-recommendation")
def record_analyst_recommendation(
    case_id: UUID,
    req: AnalystRecommendationRequest,
    fastapi_req: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(req.reason) < 10:
        raise HTTPException(
            status_code=422,
            detail="Reason is required and must be at least 10 characters",
        )

    if req.recommendation not in AnalystRecommendationAction:
        raise HTTPException(status_code=400, detail="Invalid recommendation action")

    rec_enum = req.recommendation

    case = can_view_case(db, user, case_id)

    req_hash = hashlib.sha256(
        json.dumps(req.model_dump(), sort_keys=True, default=str).encode()
    ).hexdigest()

    cached, record_id = reserve_idempotency_key(
        db,
        idempotency_key,
        req_hash,
        str(user.id),
        str(case.id),
        "analyst_recommendation",
    )
    if cached is not None:
        return cached

    ctx = can_submit_analyst_recommendation(db, case, user)
    if not ctx.allowed:
        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(
            status_code=403,
            detail={"code": ctx.blocked_reason_code, "message": ctx.message},
        )

    try:
        result_payload = {
            "status": "success",
            "recommendation": rec_enum.value,
        }

        update_values = {
            "analyst_recommendation": rec_enum.value,
            "status": CaseStatus.DECISION_PENDING.value,
        }

        cas_update_case_and_audit(
            db=db,
            case_id=case_id,
            expected_version=req.expected_version,
            update_values=update_values,
            user=user,
            action="analyst_recommendation",
            reason=req.reason,
            metadata=result_payload,
            idempotency_record_id=record_id,
        )

        return result_payload
    except HTTPException:
        raise
    except Exception:
        db.rollback()

        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(status_code=500, detail="Internal processing error")


class HumanDecisionRequest(BaseModel):
    decision: HumanDecisionAction
    reason: str
    expected_version: int
    approved_amount: Optional[Decimal] = None


@router.post("/{case_id}/human-decision")
def record_human_decision(
    case_id: UUID,
    req: HumanDecisionRequest,
    fastapi_req: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(req.reason) < 10:
        raise HTTPException(
            status_code=422,
            detail="Reason is required and must be at least 10 characters",
        )

    if req.decision not in HumanDecisionAction:
        raise HTTPException(status_code=400, detail="Invalid decision action")

    dec_enum = req.decision

    case = can_view_case(db, user, case_id)

    req_hash = hashlib.sha256(
        json.dumps(req.model_dump(), sort_keys=True, default=str).encode()
    ).hexdigest()

    cached, record_id = reserve_idempotency_key(
        db, idempotency_key, req_hash, str(user.id), str(case.id), "human_decision"
    )
    if cached is not None:
        return cached

    if (
        dec_enum == HumanDecisionAction.APPROVE_ALTERNATIVE_STRUCTURE
        and req.approved_amount is None
    ):
        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(
            status_code=422,
            detail="approved_amount is required for APPROVE_ALTERNATIVE_STRUCTURE",
        )

    ctx = can_record_human_decision(
        db, case, user, action=dec_enum, approved_amount=req.approved_amount
    )
    if not ctx.allowed:
        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(
            status_code=403,
            detail={"code": ctx.blocked_reason_code, "message": ctx.message},
        )

    try:
        result_payload: dict[str, Any] = {
            "status": "success",
            "decision": dec_enum.value,
        }
        if req.approved_amount is not None:
            result_payload["approved_amount"] = req.approved_amount

        status_val = CaseStatus.DECISION_PENDING
        if dec_enum in [
            HumanDecisionAction.APPROVE_AS_REQUESTED,
            HumanDecisionAction.APPROVE_ALTERNATIVE_STRUCTURE,
        ]:
            status_val = CaseStatus.HUMAN_APPROVED
        elif dec_enum == HumanDecisionAction.DECLINE_AFTER_HUMAN_REVIEW:
            status_val = CaseStatus.HUMAN_DECLINED
        elif dec_enum in [
            HumanDecisionAction.DEFER_FOR_EVIDENCE,
            HumanDecisionAction.ESCALATE_FOR_DUE_DILIGENCE,
        ]:
            status_val = CaseStatus.HUMAN_DEFERRED

        update_values = {
            "human_decision": dec_enum.value,
            "status": status_val.value,
        }

        cas_update_case_and_audit(
            db=db,
            case_id=case_id,
            expected_version=req.expected_version,
            update_values=update_values,
            user=user,
            action="human_decision",
            reason=req.reason,
            metadata=result_payload,
            idempotency_record_id=record_id,
        )

        return result_payload
    except HTTPException:
        raise
    except Exception:
        db.rollback()

        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(status_code=500, detail="Internal processing error")


@router.get(
    "/{case_id}/decision-package",
    response_model=DecisionPackageResponse,
    description="Fetch a full structured snapshot of the case decision package.",
)
def get_decision_package(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        cid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID")

    if not can_view_case(db, user, cid):
        raise HTTPException(
            status_code=403,
            detail="BOLA: You do not have permission to access this case.",
        )

    case = db.query(Case).filter(Case.id == cid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == cid)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )

    audit_chain = [
        DecisionPackageAuditItem(
            event_type=evt.event_type,
            actor=evt.actor,
            event_hash=evt.event_hash,
            created_at=evt.created_at.isoformat(),
        )
        for evt in audit_events
    ]

    reconciliation = DecisionPackageReconciliation(
        reconciliation_quality=case.data_confidence_score,
        evidence_confidence=case.data_confidence_score,
        source_coverage=case.resilience_score,
    )

    return DecisionPackageResponse(
        case_id=str(case.id),
        business_name=case.business.legal_name if case.business else "Unknown",
        requested_amount=case.requested_amount,
        requested_product=case.requested_product.value
        if hasattr(case.requested_product, "value")
        else case.requested_product,
        reconciliation=reconciliation,
        dscr=case.dscr,
        binding_limit=None,
        recommendation=case.recommendation,
        reason_codes=[],
        conditions=[],
        policy_version="1.0.0",
        calculation_version="1.0.0",
        analyst_action=case.analyst_recommendation,
        human_action=case.human_decision,
        case_version=case.version,
        audit_chain=audit_chain,
    )
