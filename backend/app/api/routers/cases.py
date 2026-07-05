from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
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

router = APIRouter(prefix="/api/cases", tags=["cases"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from app.services.authz import get_authorized_cases_query, check_case_read_access, check_case_mutation_access

def handle_idempotency(db: Session, key: str, req_hash: str, user_id: str, case_id: str, action: str):
    if not key:
        return None
    record = db.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key == key).first()
    if record:
        if record.request_hash != req_hash:
            raise HTTPException(status_code=400, detail="Idempotency key mismatch with payload")
        return record.response_payload
    return None

def save_idempotency_and_audit(db: Session, key: str, req_hash: str, user: User, case: Case, action: str, reason: str, payload: dict):
    # Fetch previous event for this case to build hash chain
    prev_event = db.query(AuditEvent).filter(AuditEvent.case_id == case.id).order_by(AuditEvent.created_at.desc()).first()
    
    prior_hash = prev_event.event_hash if prev_event else "GENESIS"
    
    # Deterministic payload for hashing
    hash_payload = {
        "case_id": str(case.id),
        "case_version": case.version,
        "event_type": action,
        "actor": str(user.id),
        "prior_hash": prior_hash,
        "metadata": payload
    }
    
    from fastapi.encoders import jsonable_encoder
    payload_str = json.dumps(jsonable_encoder(hash_payload), sort_keys=True)
    event_hash = hashlib.sha256((prior_hash + payload_str).encode('utf-8')).hexdigest()

    # Audit Event
    audit = AuditEvent(
        case_id=case.id,
        event_type=action,
        actor=str(user.id),
        actor_role=user.role.value,
        idempotency_key=key,
        case_version=case.version,
        reason=reason,
        metadata_json=jsonable_encoder(payload),
        prior_event_hash=prior_hash,
        event_hash=event_hash
    )
    db.add(audit)
    
    if key:
        import datetime
        idem = IdempotencyRecord(
            idempotency_key=key,
            user_id=user.id,
            case_id=case.id,
            action=action,
            request_hash=req_hash,
            response_status=200,
            response_payload=jsonable_encoder(payload),
            expires_at=utc_now() + datetime.timedelta(days=1)
        )
        db.add(idem)

@router.get("/")
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cases = get_authorized_cases_query(db, user).all()
    results = []
    for c in cases:
        results.append({
            "id": str(c.id),
            "business_id": str(c.business_id_fk),
            "status": c.status.value,
            "requested_facility_type": c.requested_facility_type,
            "requested_amount": c.requested_amount,
            "business_name": c.business.legal_name
        })
    return results

@router.get("/{case_id}")
def get_case(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = check_case_read_access(db, user, case_id)
        
    return {
        "id": str(case.id),
        "business": {
            "id": str(case.business.id),
            "business_id": case.business.business_id,
            "legal_name": case.business.legal_name,
            "sector": case.business.sector
        },
        "requested_facility_type": case.requested_facility_type,
        "requested_amount": case.requested_amount,
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    case = check_case_read_access(db, user, case_id)
    check_case_mutation_access(db, case, user, [UserRole.CREDIT_ANALYST, UserRole.SANCTIONING_AUTHORITY])
        
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True, default=str).encode()).hexdigest()
    if idempotency_key:
        cached = handle_idempotency(db, idempotency_key, req_hash, str(user.id), str(case.id), "evaluate")
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
    
    # CAS Update
    updated = db.query(Case).filter(
        Case.id == case_id,
        Case.version == req.expected_version
    ).update({
        "recommendation": decision["decision"],
        "version": Case.version + 1
    })
    
    if updated == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrency conflict during evaluation")
        
    result_payload = {
        "case_id": str(case.id),
        "business_name": case.business.legal_name,
        "features": features,
        "scores": scores,
        "decision": decision
    }
    
    save_idempotency_and_audit(db, idempotency_key, req_hash, user, case, "evaluate", "System Evaluation", result_payload)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save evaluation")
    
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if len(req.reason) < 10:
        raise HTTPException(status_code=422, detail="Reason is required and must be at least 10 characters")
        
    case = check_case_read_access(db, user, case_id)
    check_case_mutation_access(db, case, user, [UserRole.CREDIT_ANALYST])
    
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True, default=str).encode()).hexdigest()
    if idempotency_key:
        cached = handle_idempotency(db, idempotency_key, req_hash, str(user.id), str(case.id), "analyst_recommendation")
        if cached:
            return cached
            
    updated = db.query(Case).filter(
        Case.id == case_id,
        Case.version == req.expected_version
    ).update({
        "analyst_recommendation": req.recommendation,
        "version": Case.version + 1
    })
    
    if updated == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrency conflict")
        
    result_payload = {"status": "success", "recommendation": req.recommendation.value}
    save_idempotency_and_audit(db, idempotency_key, req_hash, user, case, "analyst_recommendation", req.reason, result_payload)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save recommendation")
        
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if len(req.reason) < 10:
        raise HTTPException(status_code=422, detail="Reason is required and must be at least 10 characters")
        
    case = check_case_read_access(db, user, case_id)
    check_case_mutation_access(db, case, user, [UserRole.SANCTIONING_AUTHORITY])
    
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True, default=str).encode()).hexdigest()
    if idempotency_key:
        cached = handle_idempotency(db, idempotency_key, req_hash, str(user.id), str(case.id), "human_decision")
        if cached:
            return cached
            
    updated = db.query(Case).filter(
        Case.id == case_id,
        Case.version == req.expected_version
    ).update({
        "human_decision": req.decision,
        "version": Case.version + 1
    })
    
    if updated == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrency conflict")
        
    result_payload = {"status": "success", "decision": req.decision.value}
    save_idempotency_and_audit(db, idempotency_key, req_hash, user, case, "human_decision", req.reason, result_payload)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save decision")
        
    return result_payload
