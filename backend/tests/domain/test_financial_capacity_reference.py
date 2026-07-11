import math
from app.domain.financial.engine import FinancialCapacityEngine


def test_financial_capacity_reference_term_loan():
    """
    Golden reference test for TERM_LOAN capacity and DSCR formulas independent of any database seeding.
    Verified against exact manual/golden mathematical formulas.
    """
    features = {
        "gst_metrics": {"avg_monthly_revenue": 3333333.33},  # ~4.0 Cr / yr
        "bank_metrics": {
            "operating_inflows_monthly": 3500000.0,
            "operating_outflows_monthly": 2833333.33,
            "avg_monthly_credits": 3500000.0,  # 4.2 Cr / yr -> verified annual revenue = 4.0 Cr
            "avg_monthly_debits": 2833333.33,
            "existing_monthly_emi": 100000.0,  # 12.0 Lakh / yr existing debt service
        },
        "financials": {"ebitda_reported": 6000000.0},  # 60.0 Lakh net operating cash flow annual
    }

    result = FinancialCapacityEngine.compute_capacity_from_features(
        features=features,
        requested_product="TERM_LOAN",
        requested_amount_inr=10000000.0,  # 1.0 Cr
        interest_rate_pct=13.5,
        tenure_months=36,
    )

    # 1. Check verified annual revenue and cash flows
    assert math.isclose(result["verified_revenue_annual"], 40000000.0, rel_tol=1e-3)
    assert math.isclose(result["net_operating_cash_flow_annual"], 6000000.0, rel_tol=1e-3)
    assert math.isclose(result["existing_debt_service_annual"], 1200000.0, rel_tol=1e-3)

    # 2. Check current DSCR: 60,00,000 / 12,00,000 = 5.0
    assert math.isclose(result["current_dscr"], 5.0, rel_tol=1e-4)

    # 3. Check proposed debt service for 1 Cr at 13.5% over 36 months
    # r = 0.135/12 = 0.01125. factor = 1.01125^36 = 1.4965158...
    # EMI = 1,00,00,000 * 0.01125 * 1.4965158 / 0.4965158 = 339,353.111 per month -> annual = 4,072,237.33
    assert math.isclose(result["proposed_annual_debt_service"], 4072237.33, rel_tol=1e-3)

    # 4. Check post-loan DSCR: 60,00,000 / (12,00,000 + 4,072,237.33) = 1.138
    assert math.isclose(result["post_loan_dscr"], 1.138, rel_tol=1e-2)

    # 5. Check max borrowing limit with target DSCR = 1.30
    # max_supportable_total_ds = 60,00,000 / 1.30 = 4,615,384.62
    # available_new_ds_annual = 4,615,384.62 - 1,200,000.0 = 3,415,384.62
    # available_monthly_emi = 284,615.38
    # max_principal = 284,615.38 * 0.4965158 / (0.01125 * 1.4965158) = 8,386,869.66
    assert math.isclose(result["max_borrowing_limit"], 8386869.66, rel_tol=1e-3)


def test_financial_capacity_reference_working_capital():
    """
    Golden reference test for WORKING_CAPITAL_LINE product isolation.
    Working capital lines derive limit primarily from operating cycle / inventory turn (e.g. 20% of verified GST turnover),
    subject to interest servicing coverage (DSCR).
    """
    features = {
        "gst_metrics": {"avg_monthly_revenue": 5000000.0},  # 6.0 Cr / yr
        "bank_metrics": {
            "operating_inflows_monthly": 5500000.0,
            "operating_outflows_monthly": 4200000.0,
            "avg_monthly_credits": 5500000.0,
            "avg_monthly_debits": 4200000.0,
            "existing_monthly_emi": 50000.0,  # 6.0 Lakh / yr
        },
        "financials": {"ebitda_reported": 7200000.0},  # 72 Lakh / yr
    }

    result = FinancialCapacityEngine.compute_capacity_from_features(
        features=features,
        requested_product="WORKING_CAPITAL_LINE",
        requested_amount_inr=15000000.0,  # 1.5 Cr
        interest_rate_pct=12.0,
        tenure_months=12,
    )

    # Verified annual revenue = min(6.0 Cr, 6.6 Cr) = 6.0 Cr
    # Working capital 20% of verified turnover = 1.20 Cr (1,20,00,000)
    assert math.isclose(result["verified_revenue_annual"], 60000000.0, rel_tol=1e-3)
    assert math.isclose(result["max_borrowing_limit"], 12000000.0, rel_tol=1e-3)


def test_financial_capacity_monotonicity_under_stress():
    """
    Verify that increasing stress severity (revenue drops, rate hikes, or higher debt)
    strictly decreases or preserves max borrowing limit and DSCR.
    """
    base_features = {
        "gst_metrics": {"avg_monthly_revenue": 4000000.0},
        "bank_metrics": {
            "operating_inflows_monthly": 4000000.0,
            "operating_outflows_monthly": 3000000.0,
            "avg_monthly_credits": 4000000.0,
            "avg_monthly_debits": 3000000.0,
            "existing_monthly_emi": 80000.0,
        },
        "financials": {"ebitda_reported": 8000000.0},
    }

    base = FinancialCapacityEngine.compute_capacity_from_features(
        base_features, "TERM_LOAN", 10000000.0, 13.5, 36
    )

    # Stressed: 15% revenue drop -> EBITDA drops
    stressed_features = {
        "gst_metrics": {"avg_monthly_revenue": 3400000.0},
        "bank_metrics": {
            "operating_inflows_monthly": 3400000.0,
            "operating_outflows_monthly": 3000000.0,
            "avg_monthly_credits": 3400000.0,
            "avg_monthly_debits": 3000000.0,
            "existing_monthly_emi": 80000.0,
        },
        "financials": {"ebitda_reported": 6800000.0},
    }

    stressed = FinancialCapacityEngine.compute_capacity_from_features(
        stressed_features, "TERM_LOAN", 10000000.0, 13.5, 36
    )

    assert stressed["current_dscr"] < base["current_dscr"]
    assert stressed["max_borrowing_limit"] <= base["max_borrowing_limit"]


def test_financial_capacity_missing_data_abstention():
    """
    Verify that when evidence or cash flow is insufficient or zero/negative,
    the engine gracefully returns zero limit or conservative fallback without raising unhandled errors.
    """
    empty_features = {}
    result = FinancialCapacityEngine.compute_capacity_from_features(
        empty_features, "TERM_LOAN", 5000000.0, 13.5, 36
    )

    assert result["verified_revenue_annual"] == 0.0
    assert result["max_borrowing_limit"] == 0.0
    assert result["current_dscr"] is None
    assert result["post_loan_dscr"] is None
    assert result["obligation_verification_state"] == "UNKNOWN_OBLIGATIONS"


def test_financial_capacity_does_not_use_unrestricted_credit_fallbacks():
    features = {
        "monthly_revenue_inr": 10000000,
        "monthly_expenses_inr": 1000000,
        "bank_metrics": {
            "avg_monthly_credits": 10000000,
            "avg_monthly_debits": 1000000,
        },
        "obligation_verification_state": "VERIFIED",
        "verified_existing_debt_service_monthly": 0,
    }

    result = FinancialCapacityEngine.compute_capacity_from_features(
        features, "TERM_LOAN", 5000000.0, 13.5, 36
    )

    assert result["cash_flow_status"] == "INSUFFICIENT_CASH_FLOW_DATA"
    assert result["verified_revenue_annual"] == 0.0
    assert result["max_borrowing_limit"] == 0.0
