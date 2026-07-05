from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from decimal import Decimal
from uuid import UUID
from typing import Optional, Any
from app.db.session import SessionLocal
from pydantic import BaseModel
from app.db.orm.cases import Case, HumanDecisionAction, AnalystRecommendationAction, AuditEvent, IdempotencyRecord, IdempotencyStatus, utc_now
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.api.dependencies import get_current_user, require_role
from app.db.orm.users import User, UserRole
import hashlib
import json
import datetime
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/api/cases", tags=["cases"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from app.services.authz import apply_case_list_scope, can_view_case, can_run_assessment, can_submit_analyst_recommendation, can_record_human_decision

from sqlalchemy.exc import IntegrityError
import uuid

def reserve_idempotency_key(db: Session, key: str, req_hash: str, user_id: str, case_id: str, action: str):
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
            expires_at=expires
        )
        db.add(record)
        db.commit()
        return None, record.id
    except IntegrityError:
        db.rollback()
        
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == key,
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.case_id == case_id,
            IdempotencyRecord.action == action
        ).first()
        
        if not record:
            raise HTTPException(status_code=500, detail="Idempotency conflict but record not found")
            
        if record.status == IdempotencyStatus.COMPLETED:
            if record.request_hash != req_hash:
                raise HTTPException(status_code=409, detail="Idempotency key mismatch with payload")
            return record.response_payload, record.id
            
        if record.status == IdempotencyStatus.FAILED_RETRYABLE or record.expires_at < now:
            record.status = IdempotencyStatus.IN_PROGRESS
            record.request_hash = req_hash
            record.expires_at = expires
            record.response_payload = None
            db.commit()
            return None, record.id
            
        if record.status == IdempotencyStatus.IN_PROGRESS:
            raise HTTPException(status_code=409, detail="FAILED_RETRYABLE", headers={"Retry-After": "5"})
            
        raise HTTPException(status_code=500, detail="Unknown idempotency state")

def fulfill_idempotency(db: Session, record_id: uuid.UUID, status_code: int, payload: dict):
    db.query(IdempotencyRecord).filter(
        IdempotencyRecord.id == record_id
    ).update({
        "status": IdempotencyStatus.COMPLETED,
        "response_status": status_code,
        "response_payload": payload
    })

def cas_update_case_and_audit(db: Session, case_id: UUID, expected_version: int, update_values: dict, 
                              user: User, action: str, reason: str, metadata: dict, idempotency_record_id: UUID):
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
    """)
    
    result = db.execute(update_stmt, params).fetchone()
    
    if not result:
        # Fetch current version to return in STALE_VERSION error
        current_case = db.query(Case.version).filter(Case.id == case_id).first()
        current_v = current_case.version if current_case else None
        
        # Mark as FAILED_RETRYABLE
        db.query(IdempotencyRecord).filter(IdempotencyRecord.id == idempotency_record_id).update({"status": IdempotencyStatus.FAILED_RETRYABLE})
        db.commit()
        
        raise HTTPException(
            status_code=409, 
            detail={
                "code": "STALE_VERSION",
                "current_version": current_v,
                "message": "The case has been modified by another request. Please retry with the latest version.",
                "retryable": True
            }
        )
        
    resulting_version = result[0]
    prior_version = resulting_version - 1
    
    prev_event = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.event_sequence.desc()).first()
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
        "metadata": metadata_enc
    }
    
    payload_str = json.dumps(hash_payload, sort_keys=True)
    event_hash = hashlib.sha256((prior_hash + payload_str).encode('utf-8')).hexdigest()

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
        created_at=now_utc
    )
    db.add(audit)
    
    metadata["prior_version"] = prior_version
    metadata["resulting_version"] = resulting_version
    metadata_enc["prior_version"] = prior_version
    metadata_enc["resulting_version"] = resulting_version
    
    fulfill_idempotency(db, idempotency_record_id, 200, metadata_enc)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to commit transaction")


@router.get("/")
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = utc_now()
    cases = apply_case_list_scope(db, db.query(Case), user, now).all()
    results = []
    for c in cases:
        results.append({
            "id": str(c.id),
            "business_id": str(c.business_id_fk),
            "status": c.status.value,
            "requested_amount": c.requested_amount,
            "business_name": c.business.legal_name,
            "requested_product": c.requested_product.value if c.requested_product else None
        })
    return results

@router.get("/{case_id}")
def get_case(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
        
    return {
        "id": str(case.id),
        "business": {
            "id": str(case.business.id),
            "business_id": case.business.business_id,
            "legal_name": case.business.legal_name,
            "sector": case.business.sector
        },
        "requested_amount": case.requested_amount,
        "requested_product": case.requested_product.value if case.requested_product else None,
        "currency": case.currency,
        "status": case.status.value,
        "version": case.version,
        "created_at": case.created_at,
        "updated_at": case.updated_at
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
    user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    can_run_assessment(db, case, user)
        
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True, default=str).encode()).hexdigest()
    
    cached, record_id = reserve_idempotency_key(db, idempotency_key, req_hash, str(user.id), str(case.id), "evaluate")
    if cached is not None:
        return cached
    
    # 1. Derive Features
    feature_engine = FeatureEngine(db, str(case.business_id_fk))
    features = feature_engine.derive_all_features()
    
    # 2. Score
    scorer = ScoringEngine(features)
    scores = scorer.compute_all_scores()
    
    # 3. Decision
    policy = DecisionPolicy(features, scores, Decimal(str(case.requested_amount)), case.requested_product.value)
    decision = policy.evaluate()
    
    result_payload = {
        "case_id": str(case.id),
        "business_name": case.business.legal_name,
        "features": features,
        "scores": scores,
        "decision": decision
    }
    
    update_values = {
        "recommendation": decision["decision"]
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
        idempotency_record_id=record_id
    )
    
    return result_payload

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
    user: User = Depends(get_current_user)
):
    if len(req.reason) < 10:
        raise HTTPException(status_code=422, detail="Reason is required and must be at least 10 characters")
        
    case = can_view_case(db, user, case_id)
    can_submit_analyst_recommendation(db, case, user)
    
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True, default=str).encode()).hexdigest()
    
    cached, record_id = reserve_idempotency_key(db, idempotency_key, req_hash, str(user.id), str(case.id), "analyst_recommendation")
    if cached is not None:
        return cached
            
    result_payload = {"status": "success", "recommendation": req.recommendation.value}
    
    update_values = {
        "analyst_recommendation": req.recommendation.value
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
        idempotency_record_id=record_id
    )
        
    return result_payload


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
    user: User = Depends(get_current_user)
):
    if len(req.reason) < 10:
        raise HTTPException(status_code=422, detail="Reason is required and must be at least 10 characters")
    
    if req.decision == HumanDecisionAction.APPROVE_ALTERNATIVE_STRUCTURE and req.approved_amount is None:
        raise HTTPException(status_code=422, detail="approved_amount is required for APPROVE_ALTERNATIVE_STRUCTURE")
        
    case = can_view_case(db, user, case_id)
    can_record_human_decision(db, case, user, action=req.decision, approved_amount=req.approved_amount)
    
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True, default=str).encode()).hexdigest()
    
    cached, record_id = reserve_idempotency_key(db, idempotency_key, req_hash, str(user.id), str(case.id), "human_decision")
    if cached is not None:
        return cached
            
    result_payload = {"status": "success", "decision": req.decision.value}
    if req.approved_amount is not None:
        result_payload["approved_amount"] = req.approved_amount
    
    update_values = {
        "human_decision": req.decision.value
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
        idempotency_record_id=record_id
    )
        
    return result_payload
