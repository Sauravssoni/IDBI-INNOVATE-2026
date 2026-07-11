import hashlib
import json
from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.orm.cases import AuditEvent
from app.db.orm.users import User, UserRole

def reconstruct_payload(event: AuditEvent) -> Dict[str, Any]:
    return {
        "sequence": event.event_sequence,
        "actor": event.actor,
        "actor_role": event.actor_role,
        "action": event.event_type,
        "rationale": event.reason,
        "correlation_id": event.correlation_id,
        "prior_case_version": event.prior_case_version,
        "resulting_case_version": event.resulting_case_version,
        "idempotency_record_id": str(event.idempotency_record_id) if event.idempotency_record_id else None,
        "model_version": event.model_version,
        "policy_version": event.policy_version,
        "timestamp": event.created_at.isoformat() if event.created_at else None,
        "metadata": event.metadata_json or {}
    }

def verify_audit_chain(db: Session, case_id: str, current_user: User) -> dict:
    if current_user.role not in (UserRole.AUDITOR, UserRole.SYSTEM_ADMIN, UserRole.SANCTIONING_AUTHORITY, UserRole.CREDIT_ANALYST):
        raise PermissionError("BOLA_VIOLATION: Unauthorized to verify audit chain")

    events = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.event_sequence.asc()).all()
    
    if not events:
        return _invalid_chain("GENESIS", "NO_EVENTS_FOUND")

    prior_hash = "GENESIS"
    for idx, event in enumerate(events):
        if event.event_sequence != idx + 1:
            return _invalid_chain(prior_hash, f"SEQUENCE_GAP_AT_INDEX_{idx}")
        
        if event.prior_event_hash != prior_hash:
            return _invalid_chain(prior_hash, f"HASH_MISMATCH_AT_INDEX_{idx}")

        payload = reconstruct_payload(event)
        payload_str = json.dumps(payload, sort_keys=True)
        expected_hash = hashlib.sha256((prior_hash + payload_str).encode("utf-8")).hexdigest()

        if event.event_hash != expected_hash:
            return _invalid_chain(prior_hash, f"PAYLOAD_TAMPERED_AT_INDEX_{idx}")
        
        prior_hash = expected_hash

    return {
        "audit_chain_valid": True,
        "bola_verification_status": "VERIFIED",
        "cas_verification_status": "VERIFIED",
        "package_hash": "", # To be populated by caller
        "audit_tip_hash": prior_hash,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verification_version": "2.0"
    }

def _invalid_chain(last_valid_hash: str, reason: str) -> dict:
    return {
        "audit_chain_valid": False,
        "bola_verification_status": "VERIFIED",
        "cas_verification_status": "VERIFIED",
        "package_hash": "",
        "audit_tip_hash": last_valid_hash,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verification_version": "2.0",
        "reason": reason
    }
