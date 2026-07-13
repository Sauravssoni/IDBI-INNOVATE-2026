import uuid
from app.services.assessment_service import AssessmentService
from app.db.orm.cases import Case

def test_assessment_service_no_mocked_values():
    case = Case(
        id=uuid.uuid4(),
        business_id_fk=uuid.uuid4(),
        status="ASSESSMENT_PENDING",
        requested_amount=1000000,
        requested_product="Term Loan",
        currency="INR",
        version=1
    )
    
    # Empty features and scores should NOT produce magic fallback values
    features = {}
    scores = {}
    decision = {}
    
    assessment = AssessmentService.build_assessment_result(
        case=case,
        features=features,
        scores=scores,
        decision=decision,
        cap={}
    )
    
    assert assessment.six_pillars == []
    assert assessment.financial_health_index is None
    assert assessment.vyapar_credit_health_score is None
    
    assert len(assessment.stress_results) == 1
    assert assessment.stress_results[0].scenario_name == "NOT_AVAILABLE"
    assert assessment.stress_results[0].impact == "REQUIRED_INPUTS_MISSING"
    
    assert len(assessment.bankability_interventions) == 1
    assert assessment.bankability_interventions[0].intervention_type == "NOT_AVAILABLE"
    assert assessment.bankability_interventions[0].description == "REQUIRED_INPUTS_MISSING"
    
    assert assessment.conditions == []
    assert assessment.covenants == []
    assert "Uses mocked stress test scenarios" not in assessment.limitations
