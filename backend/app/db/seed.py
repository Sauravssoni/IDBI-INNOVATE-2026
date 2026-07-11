import os
import sys
import logging
import uuid
from decimal import Decimal

# Configure path so we can import 'app' if this is run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.session import SessionLocal
from app.seed.seed_shakti import seed_shakti
from app.seed.seed_demo_principals import seed_demo_principals
from app.db.orm.cases import Case, Business, CaseStatus, AuditEvent
from app.db.orm.users import User
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.core.audit import calculate_audit_hash
from app.db.orm.cases import utc_now
from fastapi.encoders import jsonable_encoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_seed():
    db = SessionLocal()
    try:
        logger.info("Starting reliable, single-case seed (Shakti Precision)...")
        
        # 1. Seed demo principals (idempotent)
        seed_demo_principals(db)
        
        # 2. Seed exactly ONE test case (idempotent - it deletes if exists)
        seed_shakti(db)
        
        # 3. Evaluate the case so the Decision Package is fully populated
        ca_user = db.query(User).filter(User.email == "credit@bank.example").first()
        if not ca_user:
            raise Exception("credit@bank.example user not found after seeder run.")
            
        case = db.query(Case).join(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
        if not case:
            raise Exception("Shakti Precision case not found after seeder run.")
            
        logger.info("Evaluating Shakti Precision Component to generate Decision Package...")
        
        feature_engine = FeatureEngine(db, str(case.business_id_fk))
        features = feature_engine.derive_all_features()
        
        scorer = ScoringEngine(features)
        scores = scorer.compute_all_scores()
        
        policy = DecisionPolicy(
            features,
            scores,
            Decimal(str(case.requested_amount)),
            case.requested_product.value,
        )
        decision = policy.evaluate()
        
        result_payload = {
            "case_id": str(case.id),
            "business_name": case.business.legal_name,
            "features": features,
            "scores": scores,
            "decision": decision,
        }
        
        dscr_val = None
        if "bank_metrics" in features and "dscr" in features["bank_metrics"] and features["bank_metrics"]["dscr"] is not None:
            dscr_val = Decimal(str(features["bank_metrics"]["dscr"]))
            
        case.recommendation = decision["decision"]
        case.status = CaseStatus.ASSESSMENT_COMPLETED
        case.dscr = dscr_val
        prior_version = case.version
        case.version += 1
        resulting_version = case.version
        
        db.flush()
        
        prev_event = db.query(AuditEvent).filter(AuditEvent.case_id == case.id).order_by(AuditEvent.event_sequence.desc()).first()
        prior_hash = prev_event.event_hash if prev_event and prev_event.event_hash else "GENESIS"
        event_sequence = (prev_event.event_sequence + 1) if prev_event and prev_event.event_sequence else 1
        
        metadata_enc = jsonable_encoder(result_payload)
        correlation_id = str(uuid.uuid4())
        now_utc = utc_now()
        
        hash_payload = {
            "sequence": event_sequence,
            "actor": str(ca_user.id),
            "actor_role": ca_user.role.value,
            "action": "evaluate",
            "rationale": "System Evaluation via Initial Seeding",
            "correlation_id": correlation_id,
            "prior_version": prior_version,
            "resulting_version": resulting_version,
            "idempotency_record_id": None,
            "model_version": "1.0",
            "policy_version": "1.0",
            "timestamp": now_utc.isoformat(),
            "metadata": metadata_enc,
        }
        
        event_hash = calculate_audit_hash(prior_hash, hash_payload)
        
        audit_eval = AuditEvent(
            case_id=case.id,
            event_sequence=event_sequence,
            event_type="evaluate",
            actor=str(ca_user.id),
            actor_role=ca_user.role.value,
            idempotency_record_id=None,
            prior_case_version=prior_version,
            resulting_case_version=resulting_version,
            reason="System Evaluation via Initial Seeding",
            correlation_id=correlation_id,
            model_version="1.0",
            policy_version="1.0",
            metadata_json=metadata_enc,
            prior_event_hash=prior_hash,
            event_hash=event_hash,
            created_at=now_utc,
        )
        db.add(audit_eval)
        db.commit()
        
        logger.info("Successfully seeded exactly one reliable test case with a populated Decision Package.")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
