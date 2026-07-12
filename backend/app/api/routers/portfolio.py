from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.db.orm.cases import Case, CaseStatus
import json

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/metrics")
def get_portfolio_metrics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Mock data for Portfolio Assurance Lab for the prototype
    total_exposure = 150000000.00
    active_cases = db.query(Case).count()
    approved_cases = db.query(Case).filter(Case.status == CaseStatus.HUMAN_APPROVED).count()
    
    # Portfolio composition
    composition = [
        {"segment": "Manufacturing", "exposure": 80000000, "pd": 1.2, "lgd": 45},
        {"segment": "Retail", "exposure": 40000000, "pd": 2.5, "lgd": 50},
        {"segment": "Services", "exposure": 30000000, "pd": 1.8, "lgd": 40}
    ]
    
    # ECL (Expected Credit Loss) Simulation
    ecl_scenarios = {
        "base": {"ecl": 2500000, "provision_ratio": 1.6},
        "adverse": {"ecl": 4200000, "provision_ratio": 2.8},
        "severe": {"ecl": 6500000, "provision_ratio": 4.3}
    }
    
    return {
        "overview": {
            "total_exposure": total_exposure,
            "active_facilities": approved_cases * 10,
            "weighted_average_pd": 1.7,
            "weighted_average_lgd": 46.2,
            "var_99": 8500000
        },
        "composition": composition,
        "ecl_scenarios": ecl_scenarios,
        "alerts": [
            {"severity": "high", "message": "Textiles segment showing 15% increase in PD over last 30 days."},
            {"severity": "medium", "message": "3 accounts breached DSCR covenants this week."}
        ]
    }
