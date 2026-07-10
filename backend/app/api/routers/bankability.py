from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.services.authz import can_view_case
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.domain.bankability.path import compute_bankability_path

router = APIRouter(prefix="/api/cases", tags=["bankability"])


class BankabilityPathRequest(BaseModel):
    target_amount: Optional[float] = None


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
    
    requested_amount = Decimal(str(getattr(case, "requested_amount_inr", "2500000")))
    requested_product = getattr(case, "requested_product", "WORKING_CAPITAL_LINE") or "WORKING_CAPITAL_LINE"
    
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
    
    requested_amount = Decimal(str(getattr(case, "requested_amount_inr", "2500000")))
    requested_product = getattr(case, "requested_product", "WORKING_CAPITAL_LINE") or "WORKING_CAPITAL_LINE"
    
    tgt = None
    if payload and payload.target_amount is not None:
        tgt = payload.target_amount

    return compute_bankability_path(features, scores, requested_amount, requested_product, target_amount=tgt)

