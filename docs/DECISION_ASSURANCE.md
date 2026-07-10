# Decision Assurance Report

**Final SHA:** `27f572939b74c454abf51e3947a58eaa3bac1c37`
**Timestamp:** 2026-07-10T09:51:52.855844
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
- [PASS] **CA Recommendation Check**: Analyst recommendation succeeded with 200, got 200: {"status":"success","recommendation":"RECOMMEND_ALTERNATIVE_STRUCTURE","prior_version":3,"resulting_version":4,"audit_hash":"3afa2861664b18b7c87897298e4f9ea2d804c7c8d44d0487fa7dc5c3760e0af4"}
- [PASS] **SA Mandate Failure Check**: SA above-mandate approval failed with 403, got 403: {"detail":{"code":"OUTSIDE_SANCTION_MANDATE","message":"Escalation required—outside current sanction mandate."}}
- [PASS] **SA Mandate Success Check**: SA within-mandate approval succeeded with 200, got 200: {"status":"success","decision":"APPROVE_ALTERNATIVE_STRUCTURE","approved_amount":300000.0,"prior_version":4,"resulting_version":5,"audit_hash":"c2d088d8612bf9abf9497c851a6ace388bcf75accb2aa558be5b196c60bf82e7"}
- [PASS] **LLM Isolation**: LLM not called in scoring/policy verified
- [PASS] **Audit Hash Chain**: Continuous audit hash chain verified
