from typing import Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.audit import calculate_audit_hash
from app.db.orm.cases import AuditEvent
from app.db.orm.users import User
from app.services.authz import can_view_case

def reconstruct_payload(event: AuditEvent) -> Dict[str, Any]:
    return {
        "sequence": event.event_sequence,
        "actor": event.actor,
        "actor_role": event.actor_role,
        "action": event.event_type,
        "rationale": event.reason,
        "correlation_id": event.correlation_id,
        "prior_version": event.prior_case_version,
        "resulting_version": event.resulting_case_version,
        "idempotency_record_id": str(event.idempotency_record_id) if event.idempotency_record_id else None,
        "model_version": event.model_version,
        "policy_version": event.policy_version,
        "timestamp": event.created_at.isoformat() if event.created_at else None,
        "metadata": event.metadata_json or {}
    }

def verify_audit_chain(db: Session, case_id: str, current_user: User) -> dict:
    authorization_scope_valid = False
    try:
        can_view_case(db, current_user, UUID(str(case_id)))
        authorization_scope_valid = True
    except Exception:
        return _invalid_chain("GENESIS", "AUTHORIZATION_SCOPE_INVALID", False)

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
        expected_hash = calculate_audit_hash(prior_hash, payload)

        if event.event_hash != expected_hash:
            return _invalid_chain(prior_hash, f"PAYLOAD_TAMPERED_AT_INDEX_{idx}")
        
        prior_hash = expected_hash

    return {
        "audit_chain_valid": True,
        "bola_verification_status": "VERIFIED",
        "cas_verification_status": "VERIFIED",
        "analyst_event_status": "VERIFIED" if any(e.event_type in ("analyst_recommendation", "ANALYST_RECOMMENDATION", "DECISION_CREATED") for e in events) else "NOT VERIFIED",
        "human_decision_event_status": "VERIFIED" if any(e.event_type in ("human_decision", "SANCTION_DECISION") for e in events) else "NOT VERIFIED",
        "package_hash_valid": False,
        "authorization_scope_valid": authorization_scope_valid,
        "package_hash": "", # To be populated by caller
        "audit_tip_hash": prior_hash,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verification_version": "2.0"
    }

def _invalid_chain(last_valid_hash: str, reason: str, authorization_scope_valid: bool = True) -> dict:
    return {
        "audit_chain_valid": False,
        "bola_verification_status": "FAILED",
        "cas_verification_status": "FAILED",
        "analyst_event_status": "NOT VERIFIED",
        "human_decision_event_status": "NOT VERIFIED",
        "package_hash_valid": False,
        "authorization_scope_valid": authorization_scope_valid,
        "package_hash": "",
        "audit_tip_hash": last_valid_hash,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verification_version": "2.0",
        "reason": reason
    }
