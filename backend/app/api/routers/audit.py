from datetime import datetime, timezone
from typing import List, Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.db.orm.users import User, UserRole
from app.db.orm.cases import Case, AuditEvent
from app.services.authz import can_view_case, can_view_audit, apply_case_list_scope

router = APIRouter(tags=["audit"])


@router.get("/api/cases/{case_id}/audit")
@router.get("/api/audit/cases/{case_id}")
@router.get("/api/audit/cases/{case_id}/events")
def get_case_audit_trail(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    case = can_view_case(db, user, case_id)
    can_view_audit(db, case, user)

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.event_sequence.asc())
        .all()
    )

    return [
        {
            "id": str(e.id),
            "case_id": str(e.case_id),
            "event_sequence": e.event_sequence,
            "event_type": e.event_type,
            "actor": e.actor,
            "actor_role": e.actor_role,
            "prior_case_version": e.prior_case_version,
            "resulting_case_version": e.resulting_case_version,
            "prior_event_hash": e.prior_event_hash,
            "event_hash": e.event_hash,
            "reason": e.reason,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "timestamp": e.created_at.isoformat() if e.created_at else None,
            "metadata_json": e.metadata_json,
        }
        for e in events
    ]


@router.get("/api/audit/logs")
def get_recent_audit_logs(
    limit: int = Query(50, le=100, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    if user.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="System administrators cannot view case audit trails",
        )

    now = datetime.now(timezone.utc)
    scoped_cases_query = apply_case_list_scope(db, db.query(Case.id), user, now)

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id.in_(scoped_cases_query))
        .order_by(
            AuditEvent.created_at.desc(),
            AuditEvent.event_sequence.desc(),
            AuditEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(e.id),
            "case_id": str(e.case_id),
            "event_sequence": e.event_sequence,
            "event_type": e.event_type,
            "actor": e.actor,
            "actor_role": e.actor_role,
            "prior_case_version": e.prior_case_version,
            "resulting_case_version": e.resulting_case_version,
            "prior_event_hash": e.prior_event_hash,
            "event_hash": e.event_hash,
            "reason": e.reason,
            "timestamp": e.created_at.isoformat() if e.created_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "metadata_json": e.metadata_json,
        }
        for e in events
    ]
