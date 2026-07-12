import json
import os
from decimal import Decimal

def generate_manifest():
    os.makedirs("artifacts/validation", exist_ok=True)

    cases = []
    
    def make_case(cid, name, req_amt, req_prod, rev, in_flow, out_flow, emi, rate=0.135, tenure=36):
        return {
            "case_id": cid,
            "business_name": name,
            "requested_amount": req_amt,
            "requested_product": req_prod,
            "tenure_months": tenure,
            "annual_rate": rate,
            "features": {
                "bank_metrics": {
                    "operating_inflows_monthly": in_flow,
                    "operating_outflows_monthly": out_flow,
                },
                "gst_metrics": {
                    "taxable_turnover": rev
                },
                "obligation_verification_state": "VERIFIED_OBLIGATIONS",
                "verified_existing_debt_service_monthly": emi
            }
        }

    # Case 1: Perfect, requested amount is supported fully
    # Op Cash: 1M. DSCR max EMI = 1M/1.25 = 800k. New EMI space = 800k - 10k = 790k. 
    # 790k EMI -> ~ 23.3M limit. Requested 1M -> supported! Binding: REQUESTED_AMOUNT
    cases.append(make_case("CASE_001", "Perfect Enterprise", 1000000, "WORKING_CAPITAL_LINE", 50000000, 5000000, 4000000, 10000))

    # Case 2: Capped by DSCR (High obligations)
    # Op Cash: 1M. DSCR max EMI = 800k. Old EMI = 700k. New EMI space = 100k -> limit ~ 2.9M. Requested 5M. Binding: CASH_SERVICEABILITY_CAP
    cases.append(make_case("CASE_002", "Obligated Ltd", 5000000, "TERM_LOAN", 10000000, 2000000, 1000000, 700000))

    # Case 3: Capped by Absolute Product Cap (Product caps not actually implemented in limit bridge above? wait, let's see. The bridge has CASH_SERVICEABILITY_CAP and VERIFIED_OBLIGATION_CAP)
    cases.append(make_case("CASE_003", "Cash Poor Co", 3000000, "WORKING_CAPITAL_LINE", 1000000, 200000, 150000, 5000))

    # Case 4: Capped by Total Leverage. op_cash * 24.
    # Op cash 10M. 10M * 24 = 240M leverage. Requested 500M. Old debt = 0. Binding: VERIFIED_OBLIGATION_CAP
    cases.append(make_case("CASE_004", "Giant Corp", 500000000, "WORKING_CAPITAL_LINE", 200000000, 20000000, 10000000, 0))

    cases.append(make_case("CASE_005", "Invoice Factor", 5000000, "RECEIVABLES_FINANCE", 30000000, 3000000, 2500000, 10000))
    cases.append(make_case("CASE_006", "Heavy Machining", 6000000, "EQUIPMENT_FINANCE", 40000000, 4000000, 3500000, 50000))
    
    # Case 7: Zero Revenue
    cases.append(make_case("CASE_007", "Startup Nil", 1000000, "WORKING_CAPITAL_LINE", 0, 0, 0, 0))

    # Case 8: Underwater (No space)
    cases.append(make_case("CASE_008", "Underwater LLC", 2000000, "TERM_LOAN", 500000, 100000, 50000, 100000))

    cases.append(make_case("CASE_009", "Moderate Ltd", 2000000, "WORKING_CAPITAL_LINE", 8000000, 800000, 750000, 10000))
    cases.append(make_case("CASE_010", "High Ask Factor", 15000000, "RECEIVABLES_FINANCE", 50000000, 5000000, 4000000, 0))

    with open("artifacts/validation/cohort_manifest.json", "w") as f:
        json.dump(cases, f, indent=2)
        
    print(f"Generated 10 deterministic cases in artifacts/validation/cohort_manifest.json")

if __name__ == "__main__":
    generate_manifest()
