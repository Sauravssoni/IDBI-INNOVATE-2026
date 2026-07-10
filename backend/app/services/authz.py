from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from sqlalchemy.sql.expression import false
from app.db.orm.users import User, UserRole
from app.db.orm.cases import Case, HumanDecisionAction, CaseStatus, SystemRecommendation
from app.db.orm.org import UserBranchScope, SanctioningMandate, Branch
from app.schemas.responses import (
    AssessmentActionContext,
    AnalystActionContext,
    HumanActionContext,
)
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
                or_(
                    UserBranchScope.valid_from.is_(None),
                    UserBranchScope.valid_from <= now,
                ),
                or_(
                    UserBranchScope.valid_until.is_(None),
                    UserBranchScope.valid_until >= now,
                ),
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
                or_(
                    UserBranchScope.valid_from.is_(None),
                    UserBranchScope.valid_from <= now,
                ),
                or_(
                    UserBranchScope.valid_until.is_(None),
                    UserBranchScope.valid_until >= now,
                ),
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
        mandates = (
            db.query(SanctioningMandate)
            .filter(
                SanctioningMandate.user_id == user.id,
                SanctioningMandate.active.is_(True),
                or_(
                    SanctioningMandate.valid_from.is_(None),
                    SanctioningMandate.valid_from <= now,
                ),
                or_(
                    SanctioningMandate.valid_until.is_(None),
                    SanctioningMandate.valid_until >= now,
                ),
            )
            .all()
        )

        mandate_conditions = []
        for m in mandates:
            # For visibility, do not filter by maximum_amount
            conds = [
                Case.requested_product == m.product_type,
                Case.currency == m.currency,
            ]
            if m.branch_id:
                conds.append(Case.originating_branch_id == m.branch_id)
            elif m.region_id:
                # Subquery to check if case originating branch is in the region
                conds.append(
                    Case.originating_branch_id.in_(
                        db.query(Branch.id).filter(Branch.region_id == m.region_id)
                    )
                )
            mandate_conditions.append(and_(*conds))

        conditions = [Case.assigned_sanctioning_authority_id == user.id]

        if mandate_conditions:
            conditions.append(or_(*mandate_conditions))

        return query.filter(or_(*conditions))

    # Deny by default for any unknown role
    return query.filter(false())


def can_view_case(
    db: Session, user: User, case_id: UUID, now: Optional[datetime] = None
) -> Case:
    """Retrieve a case, enforcing BOLA."""
    if now is None:
        now = datetime.now(timezone.utc)
    base_query = db.query(Case)
    scoped_query = apply_case_list_scope(db, base_query, user, now)
    case = scoped_query.filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied")
    return case


def can_run_assessment(db: Session, case: Case, user: User) -> AssessmentActionContext:
    if user.role != UserRole.CREDIT_ANALYST:
        return AssessmentActionContext(
            allowed=False,
            blocked_reason_code="ROLE_NOT_AUTHORIZED",
            message="Only credit analysts can run assessments",
        )

    if case.assigned_credit_analyst_id != user.id:
        return AssessmentActionContext(
            allowed=False,
            blocked_reason_code="CASE_NOT_ASSIGNED",
            message="You are not the assigned credit analyst for this case",
        )

    if case.status not in (
        CaseStatus.INITIATED,
        CaseStatus.EVIDENCE_GATHERING,
        CaseStatus.ASSESSMENT_COMPLETED,
    ):
        return AssessmentActionContext(
            allowed=False,
            blocked_reason_code="INVALID_STATE",
            message="Assessment cannot be run in the current case state",
        )

    if case.analyst_recommendation:
        return AssessmentActionContext(
            allowed=False,
            blocked_reason_code="ANALYST_RECOMMENDATION_ALREADY_RECORDED",
            message="An analyst recommendation has already been recorded",
        )

    if case.human_decision or case.status in (
        CaseStatus.HUMAN_APPROVED,
        CaseStatus.HUMAN_DECLINED,
        CaseStatus.HUMAN_DEFERRED,
    ):
        return AssessmentActionContext(
            allowed=False,
            blocked_reason_code="HUMAN_DECISION_ALREADY_RECORDED",
            message="Human decision recorded.",
        )

    return AssessmentActionContext(allowed=True)


def can_submit_analyst_recommendation(
    db: Session, case: Case, user: User
) -> AnalystActionContext:
    if user.role != UserRole.CREDIT_ANALYST:
        return AnalystActionContext(
            allowed=False,
            blocked_reason_code="ROLE_NOT_AUTHORIZED",
            message="Only credit analysts can submit recommendations",
        )

    if case.assigned_credit_analyst_id != user.id:
        return AnalystActionContext(
            allowed=False,
            blocked_reason_code="CASE_NOT_ASSIGNED",
            message="You are not the assigned credit analyst for this case",
        )

    if case.status != CaseStatus.ASSESSMENT_COMPLETED:
        if case.status in (CaseStatus.INITIATED, CaseStatus.EVIDENCE_GATHERING):
            return AnalystActionContext(
                allowed=False,
                blocked_reason_code="ASSESSMENT_REQUIRED",
                message="Assessment must be run before a recommendation can be submitted",
            )
        return AnalystActionContext(
            allowed=False,
            blocked_reason_code="INVALID_STATE",
            message="Recommendation cannot be submitted in the current case state",
        )

    if not case.recommendation:
        return AnalystActionContext(
            allowed=False,
            blocked_reason_code="ASSESSMENT_REQUIRED",
            message="Assessment must be run before a recommendation can be submitted",
        )

    if case.analyst_recommendation:
        return AnalystActionContext(
            allowed=False,
            blocked_reason_code="ANALYST_RECOMMENDATION_ALREADY_RECORDED",
            message="An analyst recommendation has already been recorded",
        )

    if case.human_decision or case.status in (
        CaseStatus.HUMAN_APPROVED,
        CaseStatus.HUMAN_DECLINED,
        CaseStatus.HUMAN_DEFERRED,
    ):
        return AnalystActionContext(
            allowed=False,
            blocked_reason_code="HUMAN_DECISION_ALREADY_RECORDED",
            message="Human decision recorded.",
        )

    suggested_action = None
    if case.recommendation == SystemRecommendation.READY_FOR_REVIEW:
        suggested_action = "RECOMMEND_AS_REQUESTED"
    elif case.recommendation == SystemRecommendation.CONDITIONAL_OFFER:
        suggested_action = "RECOMMEND_ALTERNATIVE_STRUCTURE"
    elif case.recommendation == SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED:
        suggested_action = "REQUEST_ADDITIONAL_EVIDENCE"
    elif case.recommendation == SystemRecommendation.ENHANCED_DUE_DILIGENCE:
        suggested_action = "RECOMMEND_ENHANCED_DUE_DILIGENCE"
    elif case.recommendation == SystemRecommendation.DECLINE_RECOMMENDED:
        suggested_action = "RECOMMEND_DECLINE"

    return AnalystActionContext(allowed=True, suggested_analyst_action=suggested_action)


def can_record_human_decision(
    db: Session,
    case: Case,
    user: User,
    action: Optional[HumanDecisionAction] = None,
    approved_amount: Optional[Decimal] = None,
    now: Optional[datetime] = None,
) -> HumanActionContext:
    if case.human_decision or case.status in (
        CaseStatus.HUMAN_APPROVED,
        CaseStatus.HUMAN_DECLINED,
        CaseStatus.HUMAN_DEFERRED,
    ):
        return HumanActionContext(
            allowed=False,
            blocked_reason_code="HUMAN_DECISION_ALREADY_RECORDED",
            message="Human decision recorded.",
        )

    if user.role != UserRole.SANCTIONING_AUTHORITY:
        return HumanActionContext(
            allowed=False,
            blocked_reason_code="ROLE_NOT_AUTHORIZED",
            message="Only sanctioning authorities can record decisions",
        )

    if case.status in (
        CaseStatus.INITIATED,
        CaseStatus.EVIDENCE_GATHERING,
        CaseStatus.ASSESSMENT_COMPLETED,
    ):
        return HumanActionContext(
            allowed=False,
            blocked_reason_code="AWAITING_ANALYST_RECOMMENDATION",
            message="Awaiting Credit Analyst recommendation.",
        )

    if case.status != CaseStatus.DECISION_PENDING:
        return HumanActionContext(
            allowed=False,
            blocked_reason_code="INVALID_STATE",
            message="Decision cannot be recorded in the current state",
        )

    if not case.analyst_recommendation:
        return HumanActionContext(
            allowed=False,
            blocked_reason_code="AWAITING_ANALYST_RECOMMENDATION",
            message="Awaiting Credit Analyst recommendation.",
        )

    if now is None:
        now = datetime.now(timezone.utc)

    mandates = (
        db.query(SanctioningMandate)
        .filter(
            SanctioningMandate.user_id == user.id,
            SanctioningMandate.active.is_(True),
            or_(
                SanctioningMandate.valid_from.is_(None),
                SanctioningMandate.valid_from <= now,
            ),
            or_(
                SanctioningMandate.valid_until.is_(None),
                SanctioningMandate.valid_until >= now,
            ),
        )
        .all()
    )

    case_branch = (
        db.query(Branch).filter(Branch.id == case.originating_branch_id).first()
    )
    if not case_branch:
        return HumanActionContext(
            allowed=False,
            blocked_reason_code="INVALID_BRANCH",
            message="Case has no valid originating branch",
        )

    has_scope = False
    max_amount_limit = Decimal("0")
    for m in mandates:
        if m.product_type == case.requested_product and m.currency == case.currency:
            if (m.branch_id and m.branch_id == case.originating_branch_id) or (
                m.region_id and m.region_id == case_branch.region_id
            ):
                has_scope = True
                if m.maximum_amount > max_amount_limit:
                    max_amount_limit = m.maximum_amount

    if not has_scope:
        return HumanActionContext(
            allowed=False,
            blocked_reason_code="OUTSIDE_SANCTION_MANDATE",
            message="Escalation required—outside current sanction mandate.",
        )

    allowed_actions = [
        "DEFER_FOR_EVIDENCE",
        "ESCALATE_FOR_DUE_DILIGENCE",
        "DECLINE_AFTER_HUMAN_REVIEW",
    ]

    if case.requested_amount <= max_amount_limit and (approved_amount is None or approved_amount <= max_amount_limit):
        allowed_actions.append("APPROVE_AS_REQUESTED")
    if (approved_amount is not None and approved_amount <= max_amount_limit) or (approved_amount is None and case.requested_amount <= max_amount_limit):
        allowed_actions.append("APPROVE_ALTERNATIVE_STRUCTURE")

    if action is not None:
        if action.value not in allowed_actions:
            if action in (
                HumanDecisionAction.APPROVE_AS_REQUESTED,
                HumanDecisionAction.APPROVE_ALTERNATIVE_STRUCTURE,
            ):
                return HumanActionContext(
                    allowed=False,
                    blocked_reason_code="OUTSIDE_SANCTION_MANDATE",
                    message="Escalation required—outside current sanction mandate.",
                )
            return HumanActionContext(
                allowed=False,
                blocked_reason_code="ACTION_NOT_ALLOWED",
                message="This action is not allowed.",
            )

    suggested_human = "APPROVE_AS_REQUESTED"
    if case.analyst_recommendation:
        if case.analyst_recommendation.value == "RECOMMEND_ALTERNATIVE_STRUCTURE":
            suggested_human = "APPROVE_ALTERNATIVE_STRUCTURE"
        elif case.analyst_recommendation.value == "REQUEST_ADDITIONAL_EVIDENCE":
            suggested_human = "DEFER_FOR_EVIDENCE"
        elif case.analyst_recommendation.value == "RECOMMEND_ENHANCED_DUE_DILIGENCE":
            suggested_human = "ESCALATE_FOR_DUE_DILIGENCE"
        elif case.analyst_recommendation.value == "RECOMMEND_DECLINE":
            suggested_human = "DECLINE_AFTER_HUMAN_REVIEW"

    return HumanActionContext(
        allowed=True,
        suggested_human_action=suggested_human,
        allowed_human_actions=allowed_actions,
    )


def can_view_audit(db: Session, case: Case, user: User, now: Optional[datetime] = None):
    if user.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="System administrators cannot view case audit trails",
        )
    if user.role == UserRole.AUDITOR:
        return
    if user.role == UserRole.RISK_ADMIN:
        return
    # For others, if they can view the case, they can view the audit.
    # The check relies on the fact that `can_view_case` was already called to fetch `case` securely.
    pass
