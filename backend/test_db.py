from app.db.session import SessionLocal
from app.db.orm.cases import DecisionPackage

db = SessionLocal()
pkgs = db.query(DecisionPackage).all()
print([p.case_id for p in pkgs])
