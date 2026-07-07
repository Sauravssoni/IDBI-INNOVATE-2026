import os
import sys
from app.db.session import SessionLocal
from app.db.orm.cases import Business, Case, AuditEvent, IdempotencyRecord
from app.db.orm.evidence import GSTPeriod, BankTransaction, Invoice, InvoicePayment, EmploymentPeriod, Obligation
from app.db.orm.consents import Consent, DataConnection
from app.seed.seed_shakti import seed_shakti
from app.seed.seed_navprerna import seed_navprerna
from app.seed.seed_rangrez import seed_rangrez
from app.seed.seed_aarohan import seed_aarohan
from app.seed.run_evaluations import run_evaluations

def reset_demo():
    if os.environ.get("APP_ENV") == "production":
        print("Demo seeding is refused in production.")
        sys.exit(1)

    print("Cleaning all demo data (Cases, Evidence, Consents, Businesses)...")
    db = SessionLocal()
    try:
        # Delete idempotency and audit before cases
        db.query(AuditEvent).delete()
        db.query(IdempotencyRecord).delete()
        
        # Delete evidence
        db.query(GSTPeriod).delete()
        db.query(BankTransaction).delete()
        db.query(InvoicePayment).delete()
        db.query(Invoice).delete()
        db.query(EmploymentPeriod).delete()
        db.query(Obligation).delete()
        
        # Delete cases and consents
        db.query(DataConnection).delete()
        db.query(Consent).delete()
        db.query(Case).delete()
        
        # Finally delete businesses
        db.query(Business).delete()
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error during clean: {e}")
        sys.exit(1)
    finally:
        db.close()

    print("Seeding Shakti Precision...")
    seed_shakti()

    print("Seeding Navprerna Tech Solutions...")
    seed_navprerna()

    print("Seeding Rangrez Textiles...")
    seed_rangrez()

    print("Seeding Aarohan Infrastructure...")
    seed_aarohan()

    print("Running evaluations for advanced states...")
    run_evaluations()

    print("Demo reset complete! Precisely four personas are loaded.")

if __name__ == "__main__":
    reset_demo()
