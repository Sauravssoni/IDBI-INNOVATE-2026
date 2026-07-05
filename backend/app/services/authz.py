from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.db.orm.users import User, UserRole
from app.db.orm.cases import Case
from app.db.orm.org import UserBranchScope, SanctioningMandate
from fastapi import HTTPException
from uuid import UUID

def get_authorized_cases_query(db: Session, user: User):
    """Return an SQLAlchemy query object filtered by the user's BOLA permissions."""
    base_query = db.query(Case)

    if user.role == UserRole.SYSTEM_ADMIN:
        return base_query.filter(False)

    if user.role == UserRole.AUDITOR:
        return base_query

    if user.role == UserRole.RISK_ADMIN:
        user_branch_ids = [scope.branch_id for scope in db.query(UserBranchScope).filter(UserBranchScope.user_id == user.id)]
        if not user_branch_ids:
            return base_query.filter(False)
        return base_query.filter(Case.originating_branch_id.in_(user_branch_ids))

    if user.role == UserRole.RELATIONSHIP_MANAGER:
        user_branch_ids = [scope.branch_id for scope in db.query(UserBranchScope).filter(UserBranchScope.user_id == user.id)]
        conditions = [Case.assigned_relationship_manager_id == user.id]
        if user_branch_ids:
            conditions.append(Case.originating_branch_id.in_(user_branch_ids))
        return base_query.filter(or_(*conditions))

    if user.role == UserRole.CREDIT_ANALYST:
        return base_query.filter(Case.assigned_credit_analyst_id == user.id)

    if user.role == UserRole.SANCTIONING_AUTHORITY:
        user_branch_ids = [scope.branch_id for scope in db.query(UserBranchScope).filter(UserBranchScope.user_id == user.id)]
        mandates = db.query(SanctioningMandate).filter(SanctioningMandate.user_id == user.id).all()
        
        mandate_conditions = []
        for m in mandates:
            mandate_conditions.append(
                and_(
                    Case.requested_product == m.product,
                    Case.requested_amount <= m.max_amount
                )
            )
            
        conditions = [Case.assigned_sanctioning_authority_id == user.id]
        
        if user_branch_ids and mandate_conditions:
            conditions.append(and_(Case.originating_branch_id.in_(user_branch_ids), or_(*mandate_conditions)))
            
        return base_query.filter(or_(*conditions))

    # Deny by default for any unknown role
    return base_query.filter(False)


def check_case_read_access(db: Session, user: User, case_id: UUID) -> Case:
    """Retrieve a case, enforcing BOLA."""
    case = get_authorized_cases_query(db, user).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied")
    return case

def check_case_mutation_access(db: Session, case: Case, user: User, required_roles: list[UserRole]):
    """Enforce specific object-level conditions before mutation."""
    # First ensure they can even read it
    # We assume 'case' was retrieved via check_case_read_access
    
    if user.role not in required_roles:
        raise HTTPException(status_code=403, detail="Insufficient role for this action")

    if user.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="System administrators cannot evaluate credit cases")

    if user.role == UserRole.CREDIT_ANALYST:
        if case.assigned_credit_analyst_id and str(case.assigned_credit_analyst_id) != str(user.id):
            raise HTTPException(status_code=403, detail="You are not the assigned credit analyst for this case")

    if user.role == UserRole.RELATIONSHIP_MANAGER:
        if case.assigned_relationship_manager_id and str(case.assigned_relationship_manager_id) != str(user.id):
            raise HTTPException(status_code=403, detail="You are not the assigned relationship manager for this case")
            
    if user.role == UserRole.SANCTIONING_AUTHORITY:
        # If they are explicitly assigned, they have mutation access
        if case.assigned_sanctioning_authority_id and str(case.assigned_sanctioning_authority_id) == str(user.id):
            return
            
        # Or if it falls under their active mandate
        user_branch_ids = [scope.branch_id for scope in db.query(UserBranchScope).filter(UserBranchScope.user_id == user.id)]
        mandates = db.query(SanctioningMandate).filter(SanctioningMandate.user_id == user.id).all()
        
        has_mandate = False
        if case.originating_branch_id in user_branch_ids:
            for m in mandates:
                if case.requested_product == m.product and case.requested_amount <= m.max_amount:
                    has_mandate = True
                    break
                    
        if not has_mandate:
            raise HTTPException(status_code=403, detail="Case exceeds your sanctioning mandate or branch scope")
