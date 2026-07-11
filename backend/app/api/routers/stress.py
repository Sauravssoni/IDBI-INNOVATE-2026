from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.services.authz import can_view_case
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.domain.stress.engine import run_case_stress_lab

router = APIRouter(prefix="/api/cases", tags=["stress"])


class StressLabRequest(BaseModel):
    revenue_drop_pct: Optional[float] = 15.0
    interest_rate_hike_bps: Optional[int] = 200
    scenario: Optional[Dict[str, Any]] = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{case_id}/stress-lab")
def get_case_stress_lab(
    case_id: UUID,
    revenue_drop_pct: float = 15.0,
    interest_rate_hike_bps: int = 200,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = can_view_case(db, user, case_id)
    features = FeatureEngine(db, str(case.business_id_fk)).derive_all_features()
    scores = ScoringEngine(features).compute_all_scores()

    requested_amount = Decimal(str(getattr(case, "requested_amount_inr", "2500000")))
    requested_product = (
        getattr(case, "requested_product", "WORKING_CAPITAL_LINE")
        or "WORKING_CAPITAL_LINE"
    )

    return run_case_stress_lab(
        features,
        scores,
        requested_amount,
        requested_product,
        revenue_drop_pct=revenue_drop_pct,
        interest_rate_hike_bps=interest_rate_hike_bps,
    )


@router.post("/{case_id}/stress-lab")
def post_case_stress_lab(
    case_id: UUID,
    payload: Optional[StressLabRequest] = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = can_view_case(db, user, case_id)
    features = FeatureEngine(db, str(case.business_id_fk)).derive_all_features()
    scores = ScoringEngine(features).compute_all_scores()

    requested_amount = Decimal(str(getattr(case, "requested_amount_inr", "2500000")))
    requested_product = (
        getattr(case, "requested_product", "WORKING_CAPITAL_LINE")
        or "WORKING_CAPITAL_LINE"
    )

    rev_drop = 15.0
    rate_hike = 200
    if payload:
        if payload.scenario:
            rev_drop = float(payload.scenario.get("revenue_drop_pct", rev_drop))
            rate_hike = int(payload.scenario.get("interest_rate_hike_bps", rate_hike))
        else:
            if payload.revenue_drop_pct is not None:
                rev_drop = payload.revenue_drop_pct
            if payload.interest_rate_hike_bps is not None:
                rate_hike = payload.interest_rate_hike_bps

    return run_case_stress_lab(
        features,
        scores,
        requested_amount,
        requested_product,
        revenue_drop_pct=rev_drop,
        interest_rate_hike_bps=rate_hike,
    )
