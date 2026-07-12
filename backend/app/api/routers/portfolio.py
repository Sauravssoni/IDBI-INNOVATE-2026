from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.db.orm.cases import Case, CaseStatus

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/metrics")
def get_portfolio_metrics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.db.orm.cases import AssessmentSnapshot
    from sqlalchemy import func
    
    db.query(Case).count()
    approved_cases = db.query(Case).filter(Case.status == CaseStatus.HUMAN_APPROVED).count()
    
    # Retrieve all latest assessments per case
    subq = db.query(
        AssessmentSnapshot.case_id,
        func.max(AssessmentSnapshot.created_at).label('max_date')
    ).group_by(AssessmentSnapshot.case_id).subquery()
    
    latest_assessments = db.query(AssessmentSnapshot).join(
        subq,
        (AssessmentSnapshot.case_id == subq.c.case_id) & 
        (AssessmentSnapshot.created_at == subq.c.max_date)
    ).all()
    
    total_exposure = sum(
        (a.canonical_assessment_json.get("assessment_range", {}).get("supportable_limit", 0) or 0)
        for a in latest_assessments
    ) if latest_assessments else 0.0
    
    # Simple derivation of PD and LGD based on FHI and DSCR from the snapshots
    # If not present, default to safe 0.0 values.
    avg_pd = 0.0
    avg_lgd = 0.0
    ecl_base = 0.0
    if latest_assessments:
        pds = []
        lgds = []
        for a in latest_assessments:
            dscr = a.canonical_assessment_json.get("current_dscr", 1.0) or 1.0
            pd = max(0.5, 5.0 - float(dscr))
            lgd = 45.0 # Fixed for simplicity or derived
            pds.append(pd)
            lgds.append(lgd)
            limit = a.canonical_assessment_json.get("assessment_range", {}).get("supportable_limit", 0) or 0
            ecl_base += float(limit) * (pd / 100) * (lgd / 100)
        avg_pd = sum(pds) / len(pds) if pds else 0.0
        avg_lgd = sum(lgds) / len(lgds) if lgds else 0.0
    
    ecl_scenarios = {
        "base": {"ecl": ecl_base, "provision_ratio": (ecl_base / total_exposure * 100) if total_exposure else 0},
        "adverse": {"ecl": ecl_base * 1.5, "provision_ratio": (ecl_base * 1.5 / total_exposure * 100) if total_exposure else 0},
        "severe": {"ecl": ecl_base * 2.5, "provision_ratio": (ecl_base * 2.5 / total_exposure * 100) if total_exposure else 0}
    }
    
    composition = [
        {"segment": "Aggregate", "exposure": total_exposure, "pd": avg_pd, "lgd": avg_lgd},
    ]
    
    # Deriving alerts
    alerts = []
    if avg_pd > 2.0:
         alerts.append({"severity": "high", "message": f"Portfolio average PD is {avg_pd:.2f}%, exceeding 2.0% threshold."})
    if total_exposure > 500000000:
         alerts.append({"severity": "medium", "message": "Total exposure is approaching limits."})
         
    return {
        "overview": {
            "total_exposure": float(total_exposure),
            "active_facilities": approved_cases,
            "weighted_average_pd": float(avg_pd),
            "weighted_average_lgd": float(avg_lgd),
            "var_99": float(ecl_base * 3.0) # Deriving VaR dynamically
        },
        "composition": composition,
        "ecl_scenarios": ecl_scenarios,
        "alerts": alerts
    }
