from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from sqlalchemy.sql.expression import true, false
from app.db.orm.users import User, UserRole
from app.db.orm.cases import Case
from app.db.orm.org import UserBranchScope, SanctioningMandate
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime, timezone

def apply_case_list_scope(db: Session, query, user: User, now: datetime):
    """Return an SQLAlchemy query object filtered by the user's BOLA permissions."""
    
    if user.role == UserRole.SYSTEM_ADMIN:
        return query.filter(false())

    if user.role in (UserRole.AUDITOR, UserRole.RISK_ADMIN):
        # cases within their explicit branch scope
        user_branch_ids = [
            scope.branch_id 
            for scope in db.query(UserBranchScope).filter(
                UserBranchScope.user_id == user.id,
                UserBranchScope.active == True,
                or_(UserBranchScope.valid_from == None, UserBranchScope.valid_from <= now),
                or_(UserBranchScope.valid_until == None, UserBranchScope.valid_until >= now)
            )
        ]
        if not user_branch_ids:
            return query.filter(false())
        return query.filter(Case.originating_branch_id.in_(user_branch_ids))

    if user.role == UserRole.RELATIONSHIP_MANAGER:
        return query.filter(Case.assigned_relationship_manager_id == user.id)

    if user.role == UserRole.CREDIT_ANALYST:
        return query.filter(Case.assigned_credit_analyst_id == user.id)

    if user.role == UserRole.SANCTIONING_AUTHORITY:
        user_branch_ids = [
            scope.branch_id 
            for scope in db.query(UserBranchScope).filter(
                UserBranchScope.user_id == user.id,
                UserBranchScope.active == True,
                or_(UserBranchScope.valid_from == None, UserBranchScope.valid_from <= now),
                or_(UserBranchScope.valid_until == None, UserBranchScope.valid_until >= now)
            )
        ]
        mandates = db.query(SanctioningMandate).filter(
            SanctioningMandate.user_id == user.id,
            SanctioningMandate.active == True,
            or_(SanctioningMandate.valid_from == None, SanctioningMandate.valid_from <= now),
            or_(SanctioningMandate.valid_until == None, SanctioningMandate.valid_until >= now)
        ).all()
        
        mandate_conditions = []
        for m in mandates:
            conds = [
                Case.requested_product == m.product_type,
                Case.currency == m.currency,
                Case.requested_amount <= m.maximum_amount
            ]
            mandate_conditions.append(and_(*conds))
            
        conditions = [Case.assigned_sanctioning_authority_id == user.id]
        
        if user_branch_ids and mandate_conditions:
            # unassigned cases that fall within their active sanctioning mandate AND branch scope
            conditions.append(
                and_(
                    Case.assigned_sanctioning_authority_id == None,
                    Case.originating_branch_id.in_(user_branch_ids), 
                    or_(*mandate_conditions)
                )
            )
            
        return query.filter(or_(*conditions))

    # Deny by default for any unknown role
    return query.filter(false())


def can_view_case(db: Session, user: User, case_id: UUID, now: datetime = None) -> Case:
    """Retrieve a case, enforcing BOLA."""
    if now is None:
        now = datetime.now(timezone.utc)
    base_query = db.query(Case)
    scoped_query = apply_case_list_scope(db, base_query, user, now)
    case = scoped_query.filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied")
    return case

def can_run_assessment(db: Session, case: Case, user: User):
    if user.role != UserRole.CREDIT_ANALYST:
        raise HTTPException(status_code=403, detail="Only credit analysts can run assessments")
    if case.assigned_credit_analyst_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned credit analyst for this case")

def can_submit_analyst_recommendation(db: Session, case: Case, user: User):
    if user.role != UserRole.CREDIT_ANALYST:
        raise HTTPException(status_code=403, detail="Only credit analysts can submit recommendations")
    if case.assigned_credit_analyst_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned credit analyst for this case")

def can_record_human_decision(db: Session, case: Case, user: User, now: datetime = None):
    if user.role != UserRole.SANCTIONING_AUTHORITY:
        raise HTTPException(status_code=403, detail="Only sanctioning authorities can record decisions")
    
    if now is None:
        now = datetime.now(timezone.utc)

    if case.assigned_sanctioning_authority_id and case.assigned_sanctioning_authority_id == user.id:
        return

    # Check mandate
    user_branch_ids = [
        scope.branch_id 
        for scope in db.query(UserBranchScope).filter(
            UserBranchScope.user_id == user.id,
            UserBranchScope.active == True,
            or_(UserBranchScope.valid_from == None, UserBranchScope.valid_from <= now),
            or_(UserBranchScope.valid_until == None, UserBranchScope.valid_until >= now)
        )
    ]
    
    mandates = db.query(SanctioningMandate).filter(
        SanctioningMandate.user_id == user.id,
        SanctioningMandate.active == True,
        or_(SanctioningMandate.valid_from == None, SanctioningMandate.valid_from <= now),
        or_(SanctioningMandate.valid_until == None, SanctioningMandate.valid_until >= now)
    ).all()
    
    has_mandate = False
    if case.originating_branch_id in user_branch_ids:
        for m in mandates:
            if (case.requested_product == m.product_type and 
                case.currency == m.currency and 
                case.requested_amount <= m.maximum_amount):
                has_mandate = True
                break
                
    if not has_mandate:
        raise HTTPException(status_code=403, detail="Case exceeds your sanctioning mandate or branch scope")

def can_view_audit(db: Session, case: Case, user: User, now: datetime = None):
    # Anyone who can view the case can view the audit (checked via can_view_case first)
    if user.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="System administrators cannot view case audit trails")
    # Auditor explicitly allowed
    pass
