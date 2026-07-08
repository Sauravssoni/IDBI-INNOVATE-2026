# Decision Assurance Report

**Final SHA:** `c5d4dcf6491682c2f1ff021cd3e5996a6d146f45`
**Timestamp:** 2026-07-08T06:44:11.571107
**Policy Version:** 1
**Calculation Version:** 1

**Total Assertions:** 17
**Passed:** 17
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
- [PASS] **SA Mandate Success Check**: SA within-mandate approval succeeded with 200, got 200
- [PASS] **SA Mandate Failure Check**: SA above-mandate approval failed with 403, got 403
- [PASS] **LLM Isolation**: LLM not called in scoring/policy verified
- [PASS] **Audit Hash Chain**: Continuous audit hash chain verified
