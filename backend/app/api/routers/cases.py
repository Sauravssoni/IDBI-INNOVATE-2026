from app.schemas.responses import (
    CaseDetailResponse,
    DecisionPackageResponse,
    DecisionPackageReconciliation,
    DecisionPackageAuditItem,
    AuditVerificationResponse,
)
from app.core.versions import (
    POLICY_VERSION,
    CALCULATION_VERSION,
    SCORING_VERSION,
    PASSPORT_ENGINE_VERSION,
    FEATURE_SCHEMA_VERSION,
    PACKAGE_SCHEMA_VERSION,
    AUDIT_HASH_VERSION,
)
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from uuid import UUID
import uuid
import math
import enum
import re
from typing import Optional, Any, Dict, List
from app.db.session import SessionLocal
from pydantic import BaseModel
from app.db.orm.cases import (
    Case,
    CaseStatus,
    HumanDecisionAction,
    AnalystRecommendationAction,
    AuditEvent,
    DecisionPackage,
    IdempotencyRecord,
    IdempotencyStatus,
    utc_now,
)
from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.domain.financial.engine import FinancialCapacityEngine
from app.api.dependencies import get_current_user
from app.core.audit import calculate_audit_hash
from app.domain.audit.verification import verify_audit_chain
from app.db.orm.users import User
from app.services.assessment_service import AssessmentService
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
    idempotency_payload: Optional[dict] = None,
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

    payload_to_save = (
        jsonable_encoder(idempotency_payload)
        if idempotency_payload is not None
        else metadata_enc
    )
    fulfill_idempotency(db, idempotency_record_id, 200, payload_to_save)

    db.commit()


@router.get("/portfolio-command-centre")
def get_portfolio_command_centre(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    now = utc_now()
    cases = apply_case_list_scope(db, db.query(Case), user, now).all()

    active_cases_count = len(cases)
    total_requested_exposure = sum((c.requested_amount or Decimal(0)) for c in cases)
    
    # Calculate supportable exposure approximation from cases
    total_supportable_exposure = Decimal("0")
    status_counts: Dict[str, int] = {}
    work_queue: List[Any] = []

    for c in cases:
        st_str = c.status.value if hasattr(c.status, "value") else str(c.status)
        status_counts[st_str] = status_counts.get(st_str, 0) + 1
        
        # Determine priority and action
        priority_level = "MEDIUM"
        action_required = "Review case details and verify uploaded evidence."
        if c.recommendation == "CONDITIONAL_OFFER" or c.status == CaseStatus.ASSESSMENT_COMPLETED:
            priority_level = "HIGH"
            action_required = "High-priority: Review alternative structuring and Bankability Path actions."
            total_supportable_exposure += (c.requested_amount or Decimal(0)) * Decimal("0.80")
        elif c.recommendation == "APPROVE":
            priority_level = "HIGH"
            action_required = "Ready for Sanctioning Authority final approval and disbursement checklist."
            total_supportable_exposure += (c.requested_amount or Decimal(0))
        elif c.recommendation == "DECLINE_RECOMMENDED":
            priority_level = "LOW"
            action_required = "Review deterministic reason codes and convey 30/60/90-day improvement milestones."
            total_supportable_exposure += Decimal("0")
        else:
            total_supportable_exposure += (c.requested_amount or Decimal(0)) * Decimal("0.50")

        work_queue.append({
            "case_id": str(c.id),
            "business_name": c.business.legal_name if c.business else "Unknown MSME",
            "requested_amount": float(c.requested_amount or 0),
            "status": st_str,
            "recommendation": str(c.recommendation or "PENDING"),
            "priority_level": priority_level,
            "action_required": action_required,
            "updated_at": c.updated_at.isoformat() if c.updated_at else now.isoformat()
        })

    # Sort work_queue by priority (HIGH first)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    work_queue.sort(key=lambda x: priority_order.get(x["priority_level"], 1))

    return {
        "active_cases_count": active_cases_count,
        "total_requested_exposure": float(total_requested_exposure),
        "total_supportable_exposure": float(total_supportable_exposure),
        "status_counts": status_counts,
        "prioritized_work_queue": work_queue,
        "command_centre_version": "2.0-PORTFOLIO-CANONICAL",
    }


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
        assessment_result = AssessmentService.evaluate_case(db, case)
        latest_snapshot = AssessmentService.get_latest_assessment(db, case.id)
        features_dict = (
            latest_snapshot.feature_snapshot
            if latest_snapshot and latest_snapshot.feature_snapshot
            else {}
        )

        update_values = {
            "recommendation": assessment_result.policy_recommendation,
            "status": CaseStatus.ASSESSMENT_COMPLETED.value,
            "dscr": assessment_result.current_dscr,
        }

        cas_update_case_and_audit(
            db=db,
            case_id=case_id,
            expected_version=req.expected_version,
            update_values=update_values,
            user=user,
            action="evaluate",
            reason="System Evaluation",
            metadata={
                "assessment_id": str(assessment_result.assessment_id),
                "features": features_dict,
            },
            idempotency_record_id=record_id,
            idempotency_payload=jsonable_encoder(assessment_result),
        )

        return assessment_result
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        db.rollback()

        with SessionLocal() as tx_db:
            tx_db.query(IdempotencyRecord).filter(
                IdempotencyRecord.id == record_id
            ).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
            tx_db.commit()
        raise HTTPException(status_code=500, detail=f"Internal processing error: {exc}")


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
            idempotency_payload=result_payload.copy(),
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
            result_payload["approved_amount"] = float(req.approved_amount)

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
            idempotency_payload=result_payload.copy(),
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
    "/{case_id}/monitoring",
    description="Illustrative post-assessment monitoring extension with rule-based deterioration alerts.",
)
def get_case_monitoring(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        cid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID format")

    case = can_view_case(db, user, cid)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied")

    is_elevated = (case.recommendation in ["DECLINE_RECOMMENDED", "ADDITIONAL_EVIDENCE_REQUIRED"])

    alerts = [
        {
            "alert_code": "ALT-INFLOW-01",
            "rule_name": "Cash Inflow Decline Check",
            "status": "NORMAL",
            "threshold": "-15% vs Assessed Baseline",
            "observed_metric": "+3.2% vs Baseline",
            "detail": "Trailing 30d cash inflows show stable collection trends across linked bank accounts.",
        },
        {
            "alert_code": "ALT-BOUNCE-02",
            "rule_name": "Cheque / ECS Bounce Frequency",
            "status": "NORMAL",
            "threshold": "> 2 technical/financial bounces in 30 days",
            "observed_metric": "0 bounces",
            "detail": "Zero inward or outward cheque/ECS bounces observed across active accounts.",
        },
        {
            "alert_code": "ALT-GST-03",
            "rule_name": "GST Filing Regularity & Drop Check",
            "status": "NORMAL",
            "threshold": "Missed GSTR-3B > 10 days post due date",
            "observed_metric": "All filings on time",
            "detail": "GSTR-1 and GSTR-3B filings verified accurate up to current cycle without filing drops.",
        },
        {
            "alert_code": "ALT-CONC-04",
            "rule_name": "Top Payer Concentration Deterioration",
            "status": "TRIGGERED" if is_elevated else "NORMAL",
            "threshold": "Top 2 debtors accounting for > 60% inflows",
            "observed_metric": "68.4% concentration" if is_elevated else "34.2% concentration",
            "detail": "High customer concentration risk detected; top 2 buyers account for over 68% of inflows."
            if is_elevated
            else "Debtor concentration well diversified across 15+ recurring buyers (<40% concentration).",
        },
    ]

    return {
        "case_id": str(case.id),
        "business_name": case.business.legal_name if case.business else "Unknown MSME",
        "monitoring_status": "ACTIVE_MONITORING",
        "overall_risk_state": "ELEVATED_WATCHLIST" if is_elevated else "STABLE",
        "last_snapshot_date": "2026-07-01T00:00:00Z",
        "next_scheduled_review": "2026-10-01T00:00:00Z",
        "deterioration_alerts": alerts,
        "monitoring_engine_version": "2.0-MONITORING-CANONICAL",
    }


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

    latest_eval = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == cid, AuditEvent.event_type == "evaluate")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    metadata = latest_eval.metadata_json if latest_eval and latest_eval.metadata_json else {}
    decision_meta = metadata.get("decision", {}) if isinstance(metadata.get("decision"), dict) else {}
    scores_meta = metadata.get("scores", {}) if isinstance(metadata.get("scores"), dict) else {}

    offers = decision_meta.get("offers", [])
    binding_limit = decision_meta.get("binding_limit")
    limit_details = decision_meta.get("limit_details", [])
    post_loan_dscr = decision_meta.get("post_loan_dscr")
    reason_codes = decision_meta.get("reasons", [])

    try:
        from app.domain.evidence.passport import generate_evidence_passport
        passport = generate_evidence_passport(db, str(case.id))
    except Exception:
        passport = None

    try:
        from app.services.reconciliation import run_reconciliation
        recon = run_reconciliation(db, str(cid))
        recon_quality = Decimal(str(recon["reconciliation_match_percent"])) if recon and recon.get("reconciliation_match_percent") is not None else case.data_confidence_score
    except Exception:
        recon_quality = case.data_confidence_score

    features_dict = metadata.get("features", {}) if isinstance(metadata.get("features"), dict) else {}
    if not features_dict:
        try:
            from app.core.features.engine import FeatureEngine
            fe = FeatureEngine(db, str(case.business_id_fk))
            features_dict = fe.derive_all_features()
        except Exception:
            features_dict = {}

    if (
        not scores_meta
        or "vyapar_credit_health_score" not in scores_meta
        or "scoring_version" not in scores_meta
    ):
        try:
            from app.core.scoring.scorer import ScoringEngine
            scorer = ScoringEngine(features_dict)
            scores_meta = scorer.compute_all_scores()
        except Exception:
            pass

    evidence_confidence = Decimal(str(scores_meta["evidence_confidence_score"])) if scores_meta.get("evidence_confidence_score") is not None else case.data_confidence_score

    fhi_val = scores_meta.get("financial_health_index")
    fhi_dec = Decimal(str(fhi_val)) if fhi_val is not None else None
    credit_score_val = scores_meta.get("vyapar_credit_health_score")
    fhi_breakdown_val = scores_meta.get("fhi_breakdown")
    disclaimer_val = scores_meta.get("credit_score_disclaimer")
    scoring_ver_val = scores_meta.get("scoring_version", SCORING_VERSION)

    try:
        from app.domain.financial.engine import FinancialCapacityEngine
        cap_summary = FinancialCapacityEngine.compute_capacity_from_features(
            features_dict,
            Decimal(str(case.requested_amount)),
            case.requested_product.value
            if hasattr(case.requested_product, "value")
            else str(case.requested_product),
        )
        calc_evidence_ids = cap_summary.get("calculation_evidence_ids", {})
    except Exception:
        cap_summary = {}
        calc_evidence_ids = {}

    coverage_score = case.resilience_score
    if passport and "rail_coverage" in passport:
        cov_count = sum(1 for v in passport["rail_coverage"].values() if v)
        coverage_score = Decimal(str(cov_count * 20))

    reconciliation = DecisionPackageReconciliation(
        reconciliation_quality=recon_quality,
        evidence_confidence=evidence_confidence,
        source_coverage=coverage_score,
    )

    # CD-001: Assessment certainty derivation
    assessment_certainty = scores_meta.get("assessment_certainty")
    certainty_reasons = []
    if assessment_certainty:
        missing_material = scores_meta.get("missing_material_evidence") or []
        if missing_material:
            certainty_reasons.append(
                "Material evidence gaps remain: " + ", ".join(str(item) for item in missing_material)
            )
        else:
            certainty_reasons.append("Scoring engine found complete material evidence for this assessment.")
    elif coverage_score < 50:
        assessment_certainty = "INSUFFICIENT_TO_ASSESS"
        certainty_reasons.append("Multi-rail evidence coverage below minimum threshold (<50%).")
    elif coverage_score < 80:
        assessment_certainty = "MODERATE_CERTAINTY"
        certainty_reasons.append("Partial rail coverage across banking or tax returns.")
    else:
        assessment_certainty = "HIGH_CERTAINTY"
        certainty_reasons.append("Comprehensive multi-rail coverage across Banking, GST, Bureau, and Financials.")

    # CD-002: Synthetic peer context
    peer_context = {
        "peer_sector": case.business.sector if case.business else "Manufacturing — Auto Ancillary",
        "peer_sample_size": 48,
        "sample_status": "VALID_PEER_SAMPLE",
        "metrics_comparison": {
            "revenue_stability": {"case_score": 85, "sector_median": 72, "percentile": 78, "status": "ABOVE_MEDIAN"},
            "dscr": {"case_value": float(case.dscr) if case.dscr else 1.35, "sector_median": 1.35, "percentile": 82, "status": "ABOVE_MEDIAN"},
            "filing_regularity": {"case_score": 100, "sector_median": 88, "percentile": 90, "status": "ABOVE_MEDIAN"},
        }
    }

    try:
        from app.domain.bankability.path import compute_bankability_path
        req_product_str = str(getattr(case, "requested_product", "WORKING_CAPITAL_LINE") or "WORKING_CAPITAL_LINE")
        if hasattr(req_product_str, "value"):
            req_product_str = req_product_str.value
        bankability_path = compute_bankability_path(
            features_dict,
            scores_meta,
            Decimal(str(getattr(case, "requested_amount", getattr(case, "requested_amount_inr", "2500000")))),
            req_product_str,
        )
        if case.recommendation in ("CONDITIONAL_OFFER", "DECLINE_RECOMMENDED", "ADDITIONAL_EVIDENCE_REQUIRED"):
            conditions = [
                f"{m['milestone_id']} ({m['timeline_tier']}): {m['action']} -> Transitions decision to {m['target_state']} ({m['impact_on_score']})"
                for m in bankability_path.get("milestones", [])
            ]
        else:
            conditions = [
                f"{m['milestone_id']} ({m['timeline_tier']}): {m['action']}"
                for m in bankability_path.get("milestones", [])
            ]
    except Exception:
        bankability_path = {}
        conditions = []

    # CD-005: Hindi accessibility governed bilingual presentation
    hindi_rec_map = {
        "CONDITIONAL_OFFER": "सशर्त प्रस्ताव (Conditional Offer)",
        "DECLINE_RECOMMENDED": "अस्वीकृति अनुशंसित (Decline Recommended)",
        "APPROVE": "स्वीकृत (Approved)",
        "ADDITIONAL_EVIDENCE_REQUIRED": "अतिरिक्त साक्ष्य की आवश्यकता (Additional Evidence Required)",
    }
    missing_checklist_hindi = [
        f"{src}: {src} साक्ष्य सत्यापित या ताज़ा नहीं है (Evidence unverified/missing)"
        for src in (passport.get("missing_sources", []) + passport.get("unverified_sources", []))
    ] if passport else []
    path_actions_hindi = [
        f"{m['milestone_id']} ({m['timeline_tier']}): {m['action']} -> {m['target_state']} के लिए प्रयास करें"
        for m in bankability_path.get("milestones", [])
    ] if bankability_path else []

    hindi_summary = {
        "decision_label": hindi_rec_map.get(str(case.recommendation), "समीक्षा के लिए तैयार (Ready for Review)"),
        "reason_explanation": "आवेदक का ऋण सेवा अनुपात (DSCR) और वित्तीय साक्ष्य अनुशंसित कार्यशील पूंजी सीमा की पुष्टि करते हैं।"
        if str(case.recommendation) in ["CONDITIONAL_OFFER", "APPROVE"]
        else "वित्तीय साक्ष्य और नकदी प्रवाह वर्तमान ऋण आवेदन का समर्थन करने में असमर्थ हैं।",
        "missing_evidence_checklist": missing_checklist_hindi,
        "bankability_path_actions": path_actions_hindi,
    }

    latest_assessment = AssessmentService.get_latest_assessment(db, case.id)
    
    if latest_assessment:
        if binding_limit is None and latest_assessment.supportable_amount is not None:
            binding_limit = float(latest_assessment.supportable_amount)
        if post_loan_dscr is None and latest_assessment.post_loan_dscr is not None:
            post_loan_dscr = float(latest_assessment.post_loan_dscr)
        if not reason_codes and latest_assessment.policy_reason_codes:
            reason_codes = latest_assessment.policy_reason_codes
        if not offers and latest_assessment.offers:
            offers = latest_assessment.offers
            
        if not offers and latest_assessment.product_capacities:
            offers = []
            for cap in latest_assessment.product_capacities:
                offers.append({
                    "product_type": cap.product_name,
                    "amount": float(cap.capacity),
                    "interest_rate_pct": 11.5, # hardcoded fallback for deprecated UI component
                    "tenure_months": 36,
                    "estimated_repayment": float(cap.capacity) / 36,
                    "post_loan_dscr": post_loan_dscr,
                    "collateral_structure": "First charge on current assets",
                    "covenants": [c.covenant_text for c in latest_assessment.covenants]
                })

    if not offers or not reason_codes or binding_limit is None:
        try:
            from app.core.decision.policy import DecisionPolicy
            req_prod_str = case.requested_product.value if hasattr(case.requested_product, "value") else str(case.requested_product)
            policy_inst = DecisionPolicy(
                features_dict,
                scores_meta,
                Decimal(str(case.requested_amount)),
                req_prod_str,
            )
            policy_res = policy_inst.evaluate()
            if not offers and policy_res.get("offers"):
                offers = policy_res["offers"]
            if not reason_codes and (policy_res.get("reasons") or policy_res.get("reason_codes")):
                reason_codes = policy_res.get("reasons") or policy_res.get("reason_codes") or []
            if binding_limit is None and policy_res.get("binding_limit") is not None:
                binding_limit = float(policy_res["binding_limit"])
        except Exception:
            pass

    current_dscr_val = None
    if latest_assessment and latest_assessment.current_dscr is not None:
        current_dscr_val = latest_assessment.current_dscr
    elif cap_summary and cap_summary.get("current_dscr") is not None:
        current_dscr_val = Decimal(str(cap_summary.get("current_dscr")))
    else:
        current_dscr_val = case.dscr

    proposed_emi_val = None
    if latest_assessment and latest_assessment.proposed_emi is not None:
        proposed_emi_val = latest_assessment.proposed_emi
    elif cap_summary and cap_summary.get("proposed_emi") is not None:
        proposed_emi_val = Decimal(str(cap_summary.get("proposed_emi")))

    stressed_dscr_val = None
    if latest_assessment and hasattr(latest_assessment, "stressed_dscr") and latest_assessment.stressed_dscr is not None:
        stressed_dscr_val = latest_assessment.stressed_dscr
    elif cap_summary and cap_summary.get("stressed_dscr") is not None:
        stressed_dscr_val = Decimal(str(cap_summary.get("stressed_dscr")))

    post_loan_dscr_dec = None
    if latest_assessment and latest_assessment.post_loan_dscr is not None:
        post_loan_dscr_dec = latest_assessment.post_loan_dscr
    elif cap_summary and cap_summary.get("post_loan_dscr") is not None:
        post_loan_dscr_dec = Decimal(str(cap_summary.get("post_loan_dscr")))
    elif post_loan_dscr is not None:
        post_loan_dscr_dec = Decimal(str(post_loan_dscr))

    dp = DecisionPackageResponse(
        case_id=str(case.id),
        business_name=case.business.legal_name if case.business else "Unknown",
        requested_amount=case.requested_amount,
        requested_product=case.requested_product.value
        if hasattr(case.requested_product, "value")
        else case.requested_product,
        reconciliation=reconciliation,
        dscr=current_dscr_val or case.dscr,
        current_dscr=current_dscr_val,
        proposed_emi=proposed_emi_val,
        post_loan_dscr=post_loan_dscr_dec,
        stressed_dscr=stressed_dscr_val,
        binding_limit=Decimal(str(binding_limit)) if binding_limit is not None else None,
        recommendation=case.recommendation,
        reason_codes=reason_codes,
        conditions=conditions,
        offers=offers,
        limit_details=limit_details,
        evidence_passport=passport,
        assessment_certainty=assessment_certainty,
        certainty_reasons=certainty_reasons,
        peer_context=peer_context,
        hindi_summary=hindi_summary,
        policy_version=POLICY_VERSION,
        calculation_version=CALCULATION_VERSION,
        scoring_version=scoring_ver_val,
        financial_health_index=fhi_dec,
        vyapar_credit_health_score=credit_score_val,

        fhi_breakdown=fhi_breakdown_val,
        score_range=scores_meta.get("score_range"),
        credit_score_disclaimer=disclaimer_val,
        calculation_evidence_ids=calc_evidence_ids,
        analyst_action=case.analyst_recommendation,
        human_action=case.human_decision,
        case_version=case.version,
        audit_chain=audit_chain,
        bankability_path=bankability_path,
        assessment=latest_assessment
    )
    
    # Calculate package hash deterministically
    package_data = dp.model_dump(exclude={"package_hash"})
    dp.package_hash = _hash_package_data(package_data)
    
    return dp


def _canonical_package_json(package_data: dict[str, Any]) -> str:
    return json.dumps(
        _canonical_package_value(package_data, exclude_package_hash=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_package_value(value: Any, *, exclude_package_hash: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _canonical_package_value(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
            if not (exclude_package_hash and str(key) == "package_hash")
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_package_value(item) for item in value]
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite Decimal values are not canonicalizable")
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime.datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite float values are not canonicalizable")
        return value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"Object of type {type(value).__name__} is not canonicalizable")


def _hash_package_data(package_data: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_package_json(package_data).encode("utf-8")).hexdigest()


REQUIRED_ENGINE_VERSIONS = {
    "scoring_version": SCORING_VERSION,
    "calculation_version": CALCULATION_VERSION,
    "policy_version": POLICY_VERSION,
    "evidence_passport_version": PASSPORT_ENGINE_VERSION,
    "feature_schema_version": FEATURE_SCHEMA_VERSION,
    "package_schema_version": PACKAGE_SCHEMA_VERSION,
    "audit_hash_version": AUDIT_HASH_VERSION,
}


def _build_replay_feature_snapshot(
    features: dict[str, Any],
    evidence_snapshot: dict[str, Any],
    package_data: dict[str, Any],
) -> dict[str, Any]:
    bank_metrics = features.get("bank_metrics") if isinstance(features.get("bank_metrics"), dict) else {}
    return {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "raw_features": features,
        "consent_status": evidence_snapshot.get("consent_status"),
        "governed_bank_metrics": bank_metrics,
        "obligation_state": features.get("obligation_verification_state")
        or (evidence_snapshot.get("obligation_verification") or {}).get("state"),
        "evidence_ids": evidence_snapshot.get("authoritative_evidence_ids") or [],
        "product_request": {
            "requested_amount": package_data.get("requested_amount"),
            "requested_product": package_data.get("requested_product"),
        },
        "scoring_inputs": {
            "financial_health_features": features,
            "scoring_version": package_data.get("scoring_version"),
        },
        "calculation_inputs": {
            "requested_amount": package_data.get("requested_amount"),
            "requested_product": package_data.get("requested_product"),
            "calculation_evidence_ids": package_data.get("calculation_evidence_ids") or {},
            "bank_metrics": bank_metrics,
            "obligation_state": features.get("obligation_verification_state"),
        },
    }


def _missing_replay_snapshot_fields(snapshot: dict[str, Any]) -> list[str]:
    required = (
        "consent_status",
        "governed_bank_metrics",
        "obligation_state",
        "evidence_ids",
        "product_request",
        "scoring_inputs",
        "calculation_inputs",
    )
    missing = []
    for field in required:
        value = snapshot.get(field)
        if value is None or value == {} or value == []:
            missing.append(field)
    raw_features = snapshot.get("raw_features")
    if not isinstance(raw_features, dict) or not raw_features:
        missing.append("raw_features")
    return missing


def _sealed_package_response(record: DecisionPackage) -> dict[str, Any]:
    return {
        "package_id": record.package_id,
        "assessment_id": record.assessment_id,
        "case_id": str(record.case_id),
        "case_version": record.case_version,
        "package_hash": record.package_hash,
        "audit_tip_hash": record.audit_tip_hash,
        "engine_versions": record.engine_versions,
        "stored": True,
    }


def _semantically_equal_for_replay(original: Any, replayed: Any) -> bool:
    if isinstance(original, list) and isinstance(replayed, list):
        return len(original) == len(replayed) and all(
            _semantically_equal_for_replay(left, right)
            for left, right in zip(original, replayed)
        )
    if isinstance(original, dict) and isinstance(replayed, dict):
        return set(original.keys()) == set(replayed.keys()) and all(
            _semantically_equal_for_replay(original[key], replayed[key])
            for key in original
        )
    try:
        return Decimal(str(original)) == Decimal(str(replayed))
    except Exception:
        if isinstance(original, str) and isinstance(replayed, str):
            return _normalize_numeric_text(original) == _normalize_numeric_text(replayed)
        return original == replayed


def _normalize_numeric_text(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        raw = match.group(0)
        try:
            normalized = Decimal(raw).normalize()
            return format(normalized, "f")
        except Exception:
            return raw

    return re.sub(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])", repl, value)


@router.post("/{case_id}/decision-package")
def seal_decision_package(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        cid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID")
    case = can_view_case(db, user, cid)

    dp = get_decision_package(case_id, db, user)
    latest_eval = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == cid, AuditEvent.event_type == "evaluate")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    audit_tip = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == cid)
        .order_by(AuditEvent.event_sequence.desc())
        .first()
    )

    package_id = f"pkg_{uuid.uuid4()}"
    package_data = dp.model_dump(exclude={"package_hash"})
    package_data.update({
        "package_id": package_id,
        "assessment_id": str(latest_eval.id) if latest_eval else f"case-{case.id}-v{case.version}",
        "audit_tip_hash": audit_tip.event_hash if audit_tip else None,
        "evidence_passport_version": PASSPORT_ENGINE_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
    })

    existing = (
        db.query(DecisionPackage)
        .filter(
            DecisionPackage.case_id == case.id,
            DecisionPackage.case_version == case.version,
            DecisionPackage.assessment_id == package_data["assessment_id"],
        )
        .first()
    )
    if existing:
        return _sealed_package_response(existing)

    package_hash = _hash_package_data(package_data)
    package_data["package_hash"] = package_hash
    stored_package_data = _canonical_package_value(package_data)

    metadata = latest_eval.metadata_json if latest_eval and latest_eval.metadata_json else {}
    evidence_snapshot = package_data.get("evidence_passport") or {}
    raw_features = metadata.get("features", {}) if isinstance(metadata.get("features"), dict) else {}
    if not raw_features:
        latest_snapshot = AssessmentService.get_latest_assessment(db, case.id)
        if latest_snapshot and latest_snapshot.feature_snapshot:
            raw_features = latest_snapshot.feature_snapshot if isinstance(latest_snapshot.feature_snapshot, dict) else {}
    if not raw_features:
        try:
            from app.core.features.engine import FeatureEngine
            fe = FeatureEngine(db, str(case.business_id_fk))
            raw_features = fe.derive_all_features()
        except Exception:
            raw_features = {}
    feature_snapshot = _build_replay_feature_snapshot(raw_features, evidence_snapshot, package_data)
    missing_snapshot_fields = _missing_replay_snapshot_fields(feature_snapshot)
    if missing_snapshot_fields:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "FEATURE_SNAPSHOT_INCOMPLETE",
                "missing_fields": missing_snapshot_fields,
            },
        )
    feature_snapshot = _canonical_package_value(feature_snapshot)

    engine_versions = {
        **REQUIRED_ENGINE_VERSIONS,
    }
    human_actions = {
        "analyst_action": package_data.get("analyst_action"),
        "human_action": package_data.get("human_action"),
    }

    record = DecisionPackage(
        package_id=package_id,
        assessment_id=package_data["assessment_id"],
        case_id=case.id,
        case_version=case.version,
        canonical_json=stored_package_data,
        package_hash=package_hash,
        evidence_snapshot=evidence_snapshot,
        feature_snapshot=feature_snapshot,
        engine_versions=engine_versions,
        human_actions=human_actions,
        audit_tip_hash=package_data.get("audit_tip_hash"),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(DecisionPackage)
            .filter(
                DecisionPackage.case_id == case.id,
                DecisionPackage.case_version == case.version,
                DecisionPackage.assessment_id == package_data["assessment_id"],
            )
            .first()
        )
        if existing:
            return _sealed_package_response(existing)
        raise

    return _sealed_package_response(record)


@router.post("/{case_id}/decision-package/{package_id}/verify")
def verify_decision_package_hash(
    case_id: str,
    package_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = can_view_case(db, user, UUID(case_id))
    record = (
        db.query(DecisionPackage)
        .filter(DecisionPackage.case_id == case.id, DecisionPackage.package_id == package_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Decision package not found")
    expected_hash = record.package_hash
    actual_hash = _hash_package_data(record.canonical_json)
    return {
        "package_id": package_id,
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
        "valid": expected_hash == actual_hash,
    }


@router.post("/{case_id}/decision-package/{package_id}/replay")
def replay_decision_package(
    case_id: str,
    package_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = can_view_case(db, user, UUID(case_id))
    record = (
        db.query(DecisionPackage)
        .filter(DecisionPackage.case_id == case.id, DecisionPackage.package_id == package_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Decision package not found")
    recorded_versions = record.engine_versions or {}
    unavailable_versions = [
        {"version": key, "recorded": recorded_versions.get(key), "available": value}
        for key, value in REQUIRED_ENGINE_VERSIONS.items()
        if recorded_versions.get(key) != value
    ]
    if unavailable_versions:
        return {
            "status": "VERSION_UNAVAILABLE",
            "package_id": package_id,
            "differences": [],
            "unavailable_versions": unavailable_versions,
        }

    snapshot = record.feature_snapshot or {}
    if _missing_replay_snapshot_fields(snapshot):
        return {"status": "FEATURE_SNAPSHOT_INCOMPLETE", "package_id": package_id, "differences": []}
    features = snapshot.get("raw_features") or {}
    scores = ScoringEngine(features).compute_all_scores()
    cap = FinancialCapacityEngine.compute_capacity_from_features(
        features,
        Decimal(str(record.canonical_json.get("requested_amount", "0"))),
        record.canonical_json.get("requested_product") or "WORKING_CAPITAL_LINE",
    )
    policy = DecisionPolicy(
        features,
        scores,
        Decimal(str(record.canonical_json.get("requested_amount", "0"))),
        record.canonical_json.get("requested_product") or "WORKING_CAPITAL_LINE",
    ).evaluate()

    try:
        from app.domain.bankability.path import compute_bankability_path

        replay_bankability_path = compute_bankability_path(
            features,
            scores,
            Decimal(str(record.canonical_json.get("requested_amount", "0"))),
            record.canonical_json.get("requested_product") or "WORKING_CAPITAL_LINE",
        )
        replay_conditions = [
            f"{m['milestone_id']} ({m['timeline_tier']}): {m['action']} -> Transitions decision to {m['target_state']} ({m['impact_on_score']})"
            for m in replay_bankability_path.get("milestones", [])
        ] if policy.get("decision") in ("CONDITIONAL_OFFER", "DECLINE_RECOMMENDED", "ADDITIONAL_EVIDENCE_REQUIRED") else [
            f"{m['milestone_id']} ({m['timeline_tier']}): {m['action']}"
            for m in replay_bankability_path.get("milestones", [])
        ]
    except Exception:
        replay_bankability_path = {}
        replay_conditions = []

    selected_offer = next(
        (
            offer for offer in policy.get("offers", [])
            if offer.get("product_type") == record.canonical_json.get("requested_product")
        ),
        (policy.get("offers") or [{}])[0] if policy.get("offers") else {},
    )
    original_selected_offer = next(
        (
            offer for offer in record.canonical_json.get("offers", [])
            if offer.get("product_type") == record.canonical_json.get("requested_product")
        ),
        (record.canonical_json.get("offers") or [{}])[0] if record.canonical_json.get("offers") else {},
    )
    comparisons = {
        "financial_health_index": scores.get("financial_health_index"),
        "vyapar_credit_health_score": scores.get("vyapar_credit_health_score"),
        "assessment_certainty": scores.get("assessment_certainty"),
        "score_range": scores.get("score_range"),
        "integrity_state": features.get("integrity_state", "UNKNOWN"),
        "current_dscr": cap.get("current_dscr"),
        "proposed_emi": cap.get("proposed_emi"),
        "post_loan_dscr": cap.get("post_loan_dscr"),
        "stressed_dscr": cap.get("stressed_dscr"),
        "supportable_amount": float(Decimal(str(policy.get("binding_limit", 0) or 0))),
        "selected_product": record.canonical_json.get("requested_product"),
        "policy_recommendation": policy.get("decision"),
        "binding_rule": policy.get("missing_verification_state") or policy.get("reasons", [None])[0],
        "conditions": replay_conditions,
        "covenants": selected_offer.get("covenants", []),
    }
    original = {
        "financial_health_index": record.canonical_json.get("financial_health_index"),
        "vyapar_credit_health_score": record.canonical_json.get("vyapar_credit_health_score"),
        "assessment_certainty": record.canonical_json.get("assessment_certainty"),
        "score_range": record.canonical_json.get("score_range"),
        "integrity_state": record.canonical_json.get("integrity_state", "UNKNOWN"),
        "current_dscr": record.canonical_json.get("current_dscr") or record.canonical_json.get("dscr"),
        "proposed_emi": record.canonical_json.get("proposed_emi"),
        "post_loan_dscr": record.canonical_json.get("post_loan_dscr"),
        "stressed_dscr": record.canonical_json.get("stressed_dscr"),
        "supportable_amount": record.canonical_json.get("binding_limit"),
        "selected_product": record.canonical_json.get("requested_product"),
        "policy_recommendation": record.canonical_json.get("recommendation"),
        "binding_rule": (record.canonical_json.get("reason_codes") or [None])[0],
        "conditions": record.canonical_json.get("conditions", []),
        "covenants": original_selected_offer.get("covenants", []),
    }
    differences = [
        {"field": key, "original": original.get(key), "replayed": value}
        for key, value in comparisons.items()
        if not _semantically_equal_for_replay(original.get(key), value)
    ]
    return {
        "status": "INDEPENDENTLY_REPRODUCED" if not differences else "REPLAY_MISMATCH",
        "package_id": package_id,
        "differences": differences,
        "replayed": comparisons,
    }

@router.post("/{case_id}/verify-audit", response_model=AuditVerificationResponse)
def verify_audit_chain_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, UUID(case_id))
        
    result = verify_audit_chain(db, str(case.id), user)
    
    latest_package = (
        db.query(DecisionPackage)
        .filter(DecisionPackage.case_id == case.id)
        .order_by(DecisionPackage.created_at.desc())
        .first()
    )
    if latest_package:
        package_hash = latest_package.package_hash
        package_hash_valid = package_hash == _hash_package_data(latest_package.canonical_json)
    else:
        package_hash = ""
        package_hash_valid = False
    
    return AuditVerificationResponse(
        bola_verification_status=result["bola_verification_status"],
        cas_verification_status=result["cas_verification_status"],
        audit_chain_valid=result["audit_chain_valid"],
        analyst_event_status=result.get("analyst_event_status", "NOT VERIFIED"),
        human_decision_event_status=result.get("human_decision_event_status", "NOT VERIFIED"),
        package_hash_valid=package_hash_valid,
        authorization_scope_valid=result["authorization_scope_valid"],
        package_hash=package_hash,
        audit_tip_hash=result["audit_tip_hash"],
        verified_at=result["verified_at"],
        verification_version=result["verification_version"],
        reason=result.get("reason")
    )

@router.get("/{case_id}/assessment-result")
def get_assessment_result(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    can_view_case(db, user, case_id)
    assessment = AssessmentService.get_latest_assessment(db, case_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found")
    return assessment

@router.get("/{case_id}/assessments/{assessment_id}")
def get_assessment_by_id(case_id: UUID, assessment_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    can_view_case(db, user, case_id)
    assessment = AssessmentService.get_assessment_by_id(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if str(assessment.case_id) != str(case_id):
        raise HTTPException(status_code=400, detail="Assessment does not belong to this case")
    return assessment
from pydantic import BaseModel
from typing import Optional

class SimulationRequest(BaseModel):
    product_type: str
    amount: float
    tenure_months: int
    interest_rate: float

@router.post("/{case_id}/simulate")
def simulate_product_structure(
    case_id: UUID, req: SimulationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    # Perform a basic financial simulation for prototype
    # Dscr = Monthly Revenue / EMI
    # EMI calculation: P * r * (1 + r)^n / ((1 + r)^n - 1)
    if not case.monthly_revenue_inr:
        return {"error": "Insufficient data for simulation"}
        
    p = req.amount
    r = (req.interest_rate / 100.0) / 12.0
    n = req.tenure_months
    
    if r > 0 and n > 0:
        emi = p * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    else:
        emi = p / (n if n > 0 else 1)
        
    revenue = float(case.monthly_revenue_inr)
    dscr = revenue / emi if emi > 0 else 0
    
    # Policy checks
    viable = dscr >= 1.25
    
    return {
        "simulated_emi": emi,
        "simulated_dscr": dscr,
        "viable": viable,
        "policy_breaches": ["DSCR below 1.25"] if not viable else []
    }
