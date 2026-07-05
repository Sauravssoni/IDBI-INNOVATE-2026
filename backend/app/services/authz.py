from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from sqlalchemy.sql.expression import false
from app.db.orm.users import User, UserRole
from app.db.orm.cases import Case, HumanDecisionAction
from app.db.orm.org import UserBranchScope, SanctioningMandate, Branch
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

def apply_case_list_scope(db: Session, query, user: User, now: datetime):
    """Return an SQLAlchemy query object filtered by the user's BOLA permissions."""
    
    if user.role == UserRole.SYSTEM_ADMIN:
        return query.filter(false())

    if user.role == UserRole.AUDITOR:
        # Auditor: require explicit AUDIT scope with can_read=true
        user_branch_ids = [
            scope.branch_id 
            for scope in db.query(UserBranchScope).filter(
                UserBranchScope.user_id == user.id,
                UserBranchScope.scope_role == "AUDIT",
                UserBranchScope.can_read.is_(True),
                UserBranchScope.active.is_(True),
                or_(UserBranchScope.valid_from.is_(None), UserBranchScope.valid_from <= now),
                or_(UserBranchScope.valid_until.is_(None), UserBranchScope.valid_until >= now)
            )
        ]
        if not user_branch_ids:
            return query.filter(false())
        return query.filter(Case.originating_branch_id.in_(user_branch_ids))

    if user.role == UserRole.RISK_ADMIN:
        # Risk Admin: require explicit portfolio/risk scope
        user_branch_ids = [
            scope.branch_id 
            for scope in db.query(UserBranchScope).filter(
                UserBranchScope.user_id == user.id,
                UserBranchScope.scope_role == "RISK",
                UserBranchScope.can_read.is_(True),
                UserBranchScope.active.is_(True),
                or_(UserBranchScope.valid_from.is_(None), UserBranchScope.valid_from <= now),
                or_(UserBranchScope.valid_until.is_(None), UserBranchScope.valid_until >= now)
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
        # Visibility by explicit assignment or active valid review scope
        mandates = db.query(SanctioningMandate).filter(
            SanctioningMandate.user_id == user.id,
            SanctioningMandate.active.is_(True),
            or_(SanctioningMandate.valid_from.is_(None), SanctioningMandate.valid_from <= now),
            or_(SanctioningMandate.valid_until.is_(None), SanctioningMandate.valid_until >= now)
        ).all()
        
        mandate_conditions = []
        for m in mandates:
            # For visibility, do not filter by maximum_amount
            conds = [
                Case.requested_product == m.product_type,
                Case.currency == m.currency
            ]
            if m.branch_id:
                conds.append(Case.originating_branch_id == m.branch_id)
            elif m.region_id:
                # Subquery to check if case originating branch is in the region
                conds.append(Case.originating_branch_id.in_(
                    db.query(Branch.id).filter(Branch.region_id == m.region_id)
                ))
            mandate_conditions.append(and_(*conds))
            
        conditions = [Case.assigned_sanctioning_authority_id == user.id]
        
        if mandate_conditions:
            conditions.append(or_(*mandate_conditions))
            
        return query.filter(or_(*conditions))

    # Deny by default for any unknown role
    return query.filter(false())


def can_view_case(db: Session, user: User, case_id: UUID, now: Optional[datetime] = None) -> Case:
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

def can_record_human_decision(db: Session, case: Case, user: User, action: HumanDecisionAction, approved_amount: Optional[Decimal] = None, now: Optional[datetime] = None):
    if user.role != UserRole.SANCTIONING_AUTHORITY:
        raise HTTPException(status_code=403, detail="Only sanctioning authorities can record decisions")
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    mandates = db.query(SanctioningMandate).filter(
        SanctioningMandate.user_id == user.id,
        SanctioningMandate.active.is_(True),
        or_(SanctioningMandate.valid_from.is_(None), SanctioningMandate.valid_from <= now),
        or_(SanctioningMandate.valid_until.is_(None), SanctioningMandate.valid_until >= now)
    ).all()
    
    case_branch = db.query(Branch).filter(Branch.id == case.originating_branch_id).first()
    if not case_branch:
        raise HTTPException(status_code=500, detail="Case has no valid originating branch")

    has_mandate = False
    for m in mandates:
        # Check basic matching parameters
        if m.product_type == case.requested_product and m.currency == case.currency:
            # Check geographical scope
            if (m.branch_id and m.branch_id == case.originating_branch_id) or (m.region_id and m.region_id == case_branch.region_id):
                # Valid matching mandate scope found. Check amount if approval action.
                if action == HumanDecisionAction.APPROVE_AS_REQUESTED:
                    if case.requested_amount <= m.maximum_amount:
                        has_mandate = True
                        break
                elif action == HumanDecisionAction.APPROVE_ALTERNATIVE_STRUCTURE:
                    if approved_amount is not None and approved_amount <= m.maximum_amount:
                        has_mandate = True
                        break
                else:
                    # DEFER, ESCALATE, DECLINE
                    has_mandate = True
                    break

    if not has_mandate:
        raise HTTPException(status_code=403, detail="Case exceeds your sanctioning mandate or branch scope for this action")

def can_view_audit(db: Session, case: Case, user: User, now: Optional[datetime] = None):
    if user.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="System administrators cannot view case audit trails")
    if user.role == UserRole.AUDITOR:
        return
    if user.role == UserRole.RISK_ADMIN:
        return
    # For others, if they can view the case, they can view the audit.
    # The check relies on the fact that `can_view_case` was already called to fetch `case` securely.
    pass
