# Decision Assurance Report

**Final SHA:** `2b76e195b6d59b96d224e07b3230cfb12ed65473`
**Timestamp:** 2026-07-10T17:53:45.390741
**Policy Version:** 1
**Calculation Version:** 1

**Total Assertions:** 18
**Passed:** 18
**Failed:** 0
**Overall Result:** PASS

## Exact Persona Outputs
- **SHAKTI_PRECISION_001:** {'recommendation': 'CONDITIONAL_OFFER', 'limit': 3569042.496}
- **NAVPRERNA_TECH_001:** {'recommendation': 'ADDITIONAL_EVIDENCE_REQUIRED'}
- **RANGREZ_TEXTILES_001:** {'recommendation': 'READY_FOR_REVIEW'}
- **NIRMAAN_INFRA_001:** {'recommendation': 'DECLINE_RECOMMENDED'}

## Assertions Details
- [PASS] **Persona Count**: Found 4 businesses
- [PASS] **Case Count**: Found 4 cases
- [PASS] **Shakti Limit**: Shakti Supportable Amount ~35.7 lakh. Got 3569042.496
- [PASS] **Navprerna Recommendation**: Navprerna got ADDITIONAL_EVIDENCE_REQUIRED
- [PASS] **Rangrez Recommendation**: Rangrez got READY_FOR_REVIEW
- [PASS] **Nirmaan Recommendation**: Nirmaan got DECLINE_RECOMMENDED
- [PASS] **Idempotency Replay**: Deterministic Idempotency replay
- [PASS] **CAS STALE_VERSION**: CAS STALE_VERSION verified
- [PASS] **Cash-flow/limit Monotonicity**: cash-flow/limit monotonicity verified
- [PASS] **Obligation/DSCR Monotonicity**: obligation/DSCR monotonicity verified
- [PASS] **Evidence-confidence Monotonicity**: evidence-confidence monotonicity verified
- [PASS] **RM RBAC**: RM cannot evaluate verified
- [PASS] **Analyst RBAC**: Analyst cannot sanction verified
- [PASS] **CA Recommendation Check**: Analyst recommendation succeeded with 200, got 200: {"status":"success","recommendation":"RECOMMEND_ALTERNATIVE_STRUCTURE","prior_version":3,"resulting_version":4,"audit_hash":"edbfa9aaeede20dfc358ce4fdc601ea49cb62e4e4664b9afffec4d3becbaf8a8"}
- [PASS] **SA Mandate Failure Check**: SA above-mandate approval failed with 403, got 403: {"detail":{"code":"OUTSIDE_SANCTION_MANDATE","message":"Escalation required—outside current sanction mandate."}}
- [PASS] **SA Mandate Success Check**: SA within-mandate approval succeeded with 200, got 200: {"status":"success","decision":"APPROVE_ALTERNATIVE_STRUCTURE","approved_amount":300000.0,"prior_version":4,"resulting_version":5,"audit_hash":"5456dd73843080da28b708b1de20b3d43716fd3973110c7640cb0b41d5b0b1c9"}
- [PASS] **LLM Isolation**: LLM not called in scoring/policy verified
- [PASS] **Audit Hash Chain**: Continuous audit hash chain verified
