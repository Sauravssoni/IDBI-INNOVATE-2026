from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.db.session import SessionLocal
from pydantic import BaseModel
from app.db.orm.cases import Case, HumanDecisionAction, AnalystRecommendationAction
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.api.dependencies import get_current_user, require_role
from app.db.orm.users import User, UserRole

router = APIRouter(prefix="/api/cases", tags=["cases"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        "created_at": case.created_at,
        "updated_at": case.updated_at
    }

@router.post("/{case_id}/evaluate")
def evaluate_case(
    case_id: UUID, 
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role([UserRole.CREDIT_ANALYST]))
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Idempotency check: if case already has a recommendation, we could just return it
    # For a true idempotency key, we would store it in a separate table.
    # We will use optimistic locking here.
    
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
    
    # 4. Save back to Case (Persist) with Optimistic Concurrency
    case.recommendation = decision["decision"] # type: ignore
    case.version = case.version + 1 # type: ignore
    
    # Wrap in atomic transaction
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrency conflict during evaluation")
    
    # Return everything together
    return {
        "case_id": str(case.id),
        "business_name": case.business.legal_name,
        "features": features,
        "scores": scores,
        "decision": decision
    }

class AnalystRecommendationRequest(BaseModel):
    recommendation: AnalystRecommendationAction
    reason: str

@router.post("/{case_id}/analyst-recommendation")
def record_analyst_recommendation(
    case_id: UUID,
    req: AnalystRecommendationRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role([UserRole.CREDIT_ANALYST]))
):
    if len(req.reason) < 10:
        raise HTTPException(status_code=422, detail="Reason is required and must be at least 10 characters")
        
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case.analyst_recommendation = req.recommendation # type: ignore
    case.version = case.version + 1 # type: ignore
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrency conflict")
        
    return {"status": "success", "recommendation": req.recommendation.value}


class HumanDecisionRequest(BaseModel):
    decision: HumanDecisionAction
    reason: str

@router.post("/{case_id}/human-decision")
def record_human_decision(
    case_id: UUID,
    req: HumanDecisionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role([UserRole.SANCTIONING_AUTHORITY]))
):
    if len(req.reason) < 10:
        raise HTTPException(status_code=422, detail="Reason is required and must be at least 10 characters")
        
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case.human_decision = req.decision # type: ignore
    case.version = case.version + 1 # type: ignore
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrency conflict")
        
    return {"status": "success", "decision": req.decision.value}
