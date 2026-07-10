# Decision Assurance Report

**Final SHA:** `b261a46cc045331906dff833640bfd5deaafefa4`
**Timestamp:** 2026-07-10T11:35:22.556702
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
- **AAROHAN_INFRA_001:** {'recommendation': 'DECLINE_RECOMMENDED'}

## Assertions Details
- [PASS] **Persona Count**: Found 4 businesses
- [PASS] **Case Count**: Found 4 cases
- [PASS] **Shakti Limit**: Shakti Supportable Amount ~35.7 lakh. Got 3569042.496
- [PASS] **Navprerna Recommendation**: Navprerna got ADDITIONAL_EVIDENCE_REQUIRED
- [PASS] **Rangrez Recommendation**: Rangrez got READY_FOR_REVIEW
- [PASS] **Aarohan Recommendation**: Aarohan got DECLINE_RECOMMENDED
- [PASS] **Idempotency Replay**: Deterministic Idempotency replay
- [PASS] **CAS STALE_VERSION**: CAS STALE_VERSION verified
- [PASS] **Cash-flow/limit Monotonicity**: cash-flow/limit monotonicity verified
- [PASS] **Obligation/DSCR Monotonicity**: obligation/DSCR monotonicity verified
- [PASS] **Evidence-confidence Monotonicity**: evidence-confidence monotonicity verified
- [PASS] **RM RBAC**: RM cannot evaluate verified
- [PASS] **Analyst RBAC**: Analyst cannot sanction verified
- [PASS] **CA Recommendation Check**: Analyst recommendation succeeded with 200, got 200: {"status":"success","recommendation":"RECOMMEND_ALTERNATIVE_STRUCTURE","prior_version":3,"resulting_version":4,"audit_hash":"b442926c4e3c0637d04fd0bf0ad1d0b74a56de8c00e37bd6eab3524aaa1477ad"}
- [PASS] **SA Mandate Failure Check**: SA above-mandate approval failed with 403, got 403: {"detail":{"code":"OUTSIDE_SANCTION_MANDATE","message":"Escalation required—outside current sanction mandate."}}
- [PASS] **SA Mandate Success Check**: SA within-mandate approval succeeded with 200, got 200: {"status":"success","decision":"APPROVE_ALTERNATIVE_STRUCTURE","approved_amount":300000.0,"prior_version":4,"resulting_version":5,"audit_hash":"8549036ee112673c50955242db719de0f9d5052d0b20798a88ccee5fe34dc509"}
- [PASS] **LLM Isolation**: LLM not called in scoring/policy verified
- [PASS] **Audit Hash Chain**: Continuous audit hash chain verified
