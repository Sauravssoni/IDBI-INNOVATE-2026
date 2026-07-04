from app.engine import CreditEngine
from app.models import ScenarioRequest
from app.sample_data import DEMO_CASES


def test_hidden_champion_is_not_penalized_for_missing_bureau():
    result = CreditEngine().assess(DEMO_CASES[0])
    assert result.financial_health_score >= 70
    assert result.data_confidence_score >= 85
    assert result.decision.outcome in {"eligible", "conditional_offer"}
    assert any("No bureau history" in warning for warning in result.warnings)


def test_low_confidence_case_abstains():
    result = CreditEngine().assess(DEMO_CASES[2])
    assert result.data_confidence_score < 65
    assert result.decision.outcome == "additional_data_required"
    assert result.decision.safe_amount_inr == 0


def test_stress_scenario_reduces_or_preserves_score_not_increase_materially():
    engine = CreditEngine()
    request = ScenarioRequest(profile=DEMO_CASES[0], revenue_shock_pct=-0.25, buyer_delay_days=45)
    result = engine.simulate(request)
    assert result.stressed_score <= result.baseline_score
    assert result.stressed_dscr < DEMO_CASES[0].dscr
