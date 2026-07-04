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

def check_case_access(case: Case, user: User, required_roles: list[UserRole]):
    if user.role not in required_roles:
        raise HTTPException(status_code=403, detail="Insufficient role for this action")
        
    if user.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="System administrators cannot evaluate credit cases")
        
    if user.role == UserRole.CREDIT_ANALYST:
        if case.assigned_credit_analyst_id and str(case.assigned_credit_analyst_id) != str(user.id):
            raise HTTPException(status_code=403, detail="You are not the assigned credit analyst for this case")
            
    if user.role == UserRole.RELATIONSHIP_MANAGER:
        if case.assigned_relationship_manager_id and str(case.assigned_relationship_manager_id) != str(user.id):
            raise HTTPException(status_code=403, detail="You are not the assigned relationship manager for this case")

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
    # Audit Event
    audit = AuditEvent(
        case_id=case.id,
        event_type=action,
        actor=str(user.id),
        actor_role=user.role.value,
        idempotency_key=key,
        case_version=case.version,
        reason=reason,
        metadata_json=payload
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
            response_payload=payload,
            expires_at=utc_now() + datetime.timedelta(days=1)
        )
        db.add(idem)

@router.get("/")
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cases = db.query(Case).all()
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
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
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
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    check_case_access(case, user, [UserRole.CREDIT_ANALYST, UserRole.SANCTIONING_AUTHORITY])
        
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True).encode()).hexdigest()
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
    policy = DecisionPolicy(features, scores, Decimal(str(case.requested_amount)), str(case.requested_facility_type))
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
        
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    check_case_access(case, user, [UserRole.CREDIT_ANALYST])
    
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True).encode()).hexdigest()
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
        
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    check_case_access(case, user, [UserRole.SANCTIONING_AUTHORITY])
    
    req_hash = hashlib.sha256(json.dumps(req.model_dump(), sort_keys=True).encode()).hexdigest()
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
