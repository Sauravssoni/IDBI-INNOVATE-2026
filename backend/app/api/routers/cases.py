from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from uuid import UUID
from typing import Optional, Any
from app.db.session import SessionLocal
from pydantic import BaseModel
from app.db.orm.cases import Case, HumanDecisionAction, AnalystRecommendationAction, AuditEvent, IdempotencyRecord, utc_now
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

def reserve_idempotency_key(db: Session, key: str, req_hash: str, user_id: str, case_id: str, action: str):
    """
    Atomically reserve the idempotency key.
    If it exists and is done, returns the cached payload.
    If it exists and is in progress, raises 409 FAILED_RETRYABLE.
    If it doesn't exist, creates an IN_PROGRESS record and returns None.
    """
    # Use postgres INSERT ... ON CONFLICT DO NOTHING to avoid race conditions
    insert_stmt = text("""
        INSERT INTO idempotency_records (id, idempotency_key, user_id, case_id, action, request_hash, created_at, updated_at, expires_at)
        VALUES (gen_random_uuid(), :key, :user_id, :case_id, :action, :req_hash, :now, :now, :expires)
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
    """)
    now = utc_now()
    expires = now + datetime.timedelta(days=1)
    
    result = db.execute(insert_stmt, {
        "key": key,
        "user_id": user_id,
        "case_id": case_id,
        "action": action,
        "req_hash": req_hash,
        "now": now,
        "expires": expires
    }).fetchone()
    
    if result:
        # Successfully reserved IN_PROGRESS
        db.commit()
        return None
        
    # If we get here, the key already exists
    record = db.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key == key).first()
    if not record:
        raise HTTPException(status_code=500, detail="Idempotency record conflict error")
        
    if record.request_hash != req_hash:
        raise HTTPException(status_code=400, detail="Idempotency key mismatch with payload")
        
    if record.response_status is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="FAILED_RETRYABLE")
        
    return record.response_payload

def fulfill_idempotency(db: Session, key: str, status_code: int, payload: dict):
    db.query(IdempotencyRecord).filter(
        IdempotencyRecord.idempotency_key == key
    ).update({
        "response_status": status_code,
        "response_payload": payload
    })

def cas_update_case_and_audit(db: Session, case_id: UUID, expected_version: int, update_values: dict, 
                              user: User, action: str, reason: str, metadata: dict, idempotency_key: str):
    """
    Perform a Compare-And-Swap (CAS) update on the Case, append to AuditEvent, and fulfill idempotency atomically.
    """
    # 1. Lock the Case row and get current state
    # Wait, using UPDATE ... RETURNING handles the lock implicitly for the case, but we need prior event for hash chain.
    
    # We will execute the UPDATE with RETURNING
    # But first, we need prior_hash. So we lock the audit chain or rely on the transaction.
    
    # UPDATE cases
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
        raise HTTPException(status_code=409, detail="Concurrency conflict")
        
    resulting_version = result[0]
    prior_version = resulting_version - 1
    
    # Fetch previous event for this case to build hash chain
    prev_event = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at.desc()).first()
    prior_hash = prev_event.event_hash if prev_event else "GENESIS"
    
    metadata_enc = jsonable_encoder(metadata)
    
    # Deterministic payload for hashing
    hash_payload = {
        "case_id": str(case_id),
        "case_version": resulting_version,
        "event_type": action,
        "actor": str(user.id),
        "prior_hash": prior_hash,
        "metadata": metadata_enc
    }
    
    payload_str = json.dumps(hash_payload, sort_keys=True)
    event_hash = hashlib.sha256((prior_hash + payload_str).encode('utf-8')).hexdigest()

    # Audit Event
    audit = AuditEvent(
        case_id=case_id,
        event_type=action,
        actor=str(user.id),
        actor_role=user.role.value,
        idempotency_key=idempotency_key,
        case_version=resulting_version,
        reason=reason,
        metadata_json=metadata_enc,
        prior_event_hash=prior_hash,
        event_hash=event_hash
    )
    db.add(audit)
    
    # Fulfill Idempotency
    fulfill_idempotency(db, idempotency_key, 200, metadata_enc)
    
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
    
    cached = reserve_idempotency_key(db, idempotency_key, req_hash, str(user.id), str(case.id), "evaluate")
    if cached:
        return cached
    
    # 1. Derive Features
    feature_engine = FeatureEngine(db, str(case.business_id_fk))
    features = feature_engine.derive_all_features()
    
    # 2. Score
    scorer = ScoringEngine(features)
    scores = scorer.compute_all_scores()
    
    # 3. Decision
    from decimal import Decimal
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
        idempotency_key=idempotency_key
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
    
    cached = reserve_idempotency_key(db, idempotency_key, req_hash, str(user.id), str(case.id), "analyst_recommendation")
    if cached:
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
        idempotency_key=idempotency_key
    )
        
    return result_payload


class HumanDecisionRequest(BaseModel):
    decision: HumanDecisionAction
    reason: str
    expected_version: int

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
        
    case = can_view_case(db, user, case_id)
    can_record_human_decision(db, case, user)
    
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True, default=str).encode()).hexdigest()
    
    cached = reserve_idempotency_key(db, idempotency_key, req_hash, str(user.id), str(case.id), "human_decision")
    if cached:
        return cached
            
    result_payload = {"status": "success", "decision": req.decision.value}
    
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
        idempotency_key=idempotency_key
    )
        
    return result_payload
