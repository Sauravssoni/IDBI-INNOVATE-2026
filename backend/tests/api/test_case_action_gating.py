import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from decimal import Decimal
from app.db.orm.users import User, UserRole
from app.db.orm.cases import Case, CaseStatus, SystemRecommendation, AnalystRecommendationAction, HumanDecisionAction
from app.db.orm.org import Branch, SanctioningMandate
from app.services.authz import can_run_assessment, can_submit_analyst_recommendation, can_record_human_decision

def _create_mock_user(role, user_id=1):
    user = User(id=user_id, email="test@bank.example", role=role, is_active=True)
    return user

def _create_mock_case(status, assigned_ca_id=1, recommendation=None, analyst_rec=None, human_dec=None):
    case = Case(
        id="uuid-1", 
        status=status,
        assigned_credit_analyst_id=assigned_ca_id,
        recommendation=recommendation,
        originating_branch_id="b1",
        requested_product="WORKING_CAPITAL_LINE",
        currency="INR",
        requested_amount=Decimal('500000.00')
    )
    if analyst_rec:
        case.analyst_recommendation = analyst_rec
    if human_dec:
        case.human_decision = human_dec
    return case

def test_ca_run_assessment_success():
    user = _create_mock_user(UserRole.CREDIT_ANALYST)
    case = _create_mock_case(CaseStatus.INITIATED)
    ctx = can_run_assessment(None, case, user)
    assert ctx.allowed is True

def test_ca_run_assessment_blocked_wrong_role():
    user = _create_mock_user(UserRole.SANCTIONING_AUTHORITY)
    case = _create_mock_case(CaseStatus.INITIATED)
    ctx = can_run_assessment(None, case, user)
    assert ctx.allowed is False
    assert ctx.blocked_reason_code == "ROLE_NOT_AUTHORIZED"

def test_ca_submit_rec_success():
    user = _create_mock_user(UserRole.CREDIT_ANALYST)
    case = _create_mock_case(CaseStatus.ASSESSMENT_COMPLETED, recommendation=SystemRecommendation.READY_FOR_REVIEW)
    ctx = can_submit_analyst_recommendation(None, case, user)
    assert ctx.allowed is True
    assert ctx.suggested_analyst_action == "RECOMMEND_AS_REQUESTED"

class MockDB:
    def __init__(self, mandates, branch):
        self.mandates = mandates
        self.branch = branch
    def query(self, model):
        class QueryMock:
            def __init__(self, db, model):
                self.db = db
                self.model = model
            def filter(self, *args, **kwargs):
                return self
            def first(self):
                if self.model == Branch:
                    return self.db.branch
                return None
            def all(self):
                if self.model == SanctioningMandate:
                    return self.db.mandates
                return []
        return QueryMock(self, model)

def test_sa_record_decision_success():
    user = _create_mock_user(UserRole.SANCTIONING_AUTHORITY)
    case = _create_mock_case(CaseStatus.DECISION_PENDING)
    case.analyst_recommendation = AnalystRecommendationAction.RECOMMEND_AS_REQUESTED
    
    mandate = SanctioningMandate(
        user_id=1, product_type="WORKING_CAPITAL_LINE", currency="INR", maximum_amount=Decimal('1000000.00'),
        branch_id="b1", region_id=None, active=True
    )
    branch = Branch(id="b1", region_id="r1")
    db = MockDB([mandate], branch)
    
    ctx = can_record_human_decision(db, case, user)
    assert ctx.allowed is True
    assert ctx.suggested_human_action == "APPROVE_AS_REQUESTED"
    assert "APPROVE_AS_REQUESTED" in ctx.allowed_human_actions

