from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.db.session import SessionLocal
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.services.authz import can_view_case
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.domain.bankability.path import compute_bankability_path, simulate_bankability_variable

router = APIRouter(prefix="/api/cases", tags=["bankability"])
simulation_router = APIRouter(prefix="/api/bankability", tags=["bankability"])


class BankabilityPathRequest(BaseModel):
    target_amount: Optional[float] = None


class BankabilitySimulationRequest(BaseModel):
    case_id: Optional[UUID] = None
    target_amount: Optional[float] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{case_id}/bankability-path")
def get_case_bankability_path(
    case_id: UUID,
    target_amount: Optional[float] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    features = FeatureEngine(db, str(case.business_id_fk)).derive_all_features()
    scores = ScoringEngine(features).compute_all_scores()
    
    requested_amount = Decimal(str(getattr(case, "requested_amount", getattr(case, "requested_amount_inr", "2500000"))))
    requested_product = str(getattr(case, "requested_product", "WORKING_CAPITAL_LINE") or "WORKING_CAPITAL_LINE")
    if hasattr(requested_product, "value"):
        requested_product = requested_product.value
    
    return compute_bankability_path(features, scores, requested_amount, requested_product, target_amount=target_amount)


@router.post("/{case_id}/bankability-path")
def post_case_bankability_path(
    case_id: UUID,
    payload: Optional[BankabilityPathRequest] = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    features = FeatureEngine(db, str(case.business_id_fk)).derive_all_features()
    scores = ScoringEngine(features).compute_all_scores()
    
    requested_amount = Decimal(str(getattr(case, "requested_amount", getattr(case, "requested_amount_inr", "2500000"))))
    requested_product = str(getattr(case, "requested_product", "WORKING_CAPITAL_LINE") or "WORKING_CAPITAL_LINE")
    if hasattr(requested_product, "value"):
        requested_product = requested_product.value
    
    tgt = None
    if payload and payload.target_amount is not None:
        tgt = payload.target_amount

    return compute_bankability_path(features, scores, requested_amount, requested_product, target_amount=tgt)


@router.post("/{case_id}/simulate")
@router.post("/{case_id}/bankability/simulate")
def post_case_bankability_simulate(
    case_id: UUID,
    payload: Optional[BankabilitySimulationRequest] = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    features = FeatureEngine(db, str(case.business_id_fk)).derive_all_features()
    scores = ScoringEngine(features).compute_all_scores()
    
    requested_amount = Decimal(str(getattr(case, "requested_amount", getattr(case, "requested_amount_inr", "2500000"))))
    requested_product = str(getattr(case, "requested_product", "WORKING_CAPITAL_LINE") or "WORKING_CAPITAL_LINE")
    if hasattr(requested_product, "value"):
        requested_product = requested_product.value
        
    overrides = payload.overrides if payload and payload.overrides else {}
    return simulate_bankability_variable(features, scores, requested_amount, requested_product, overrides)


@simulation_router.post("/simulate")
def post_standalone_bankability_simulate(
    payload: Optional[BankabilitySimulationRequest] = Body(None),
    case_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    cid = case_id or (payload.case_id if payload else None)
    if not cid:
        from app.db.orm.cases import Business
        business = db.query(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
        if business and business.cases:
            cid = business.cases[0].id
        else:
            raise HTTPException(status_code=400, detail="case_id required")
            
    case = can_view_case(db, user, cid)
    features = FeatureEngine(db, str(case.business_id_fk)).derive_all_features()
    scores = ScoringEngine(features).compute_all_scores()
    
    requested_amount = Decimal(str(getattr(case, "requested_amount", getattr(case, "requested_amount_inr", "2500000"))))
    requested_product = str(getattr(case, "requested_product", "WORKING_CAPITAL_LINE") or "WORKING_CAPITAL_LINE")
    if hasattr(requested_product, "value"):
        requested_product = requested_product.value
        
    overrides = payload.overrides if payload and payload.overrides else {}
    return simulate_bankability_variable(features, scores, requested_amount, requested_product, overrides)


