# Vyapar Pulse — Final Evidence Report (`v1.0.1-idbi-submission-final`)

**Status**: Final hackathon release candidate (`v1.0.1-idbi-submission-final`)  
**Live Production URL**: [https://frontend-swart-ten-40haipc0xl.vercel.app](https://frontend-swart-ten-40haipc0xl.vercel.app)  
**Live Backend API**: [https://vyapar-pulse-backend.vercel.app/docs](https://vyapar-pulse-backend.vercel.app/docs)  
**Single Source of Truth**: Canonical `AssessmentResultResponse` directly embedded inside `DecisionPackageResponse` (`0% data drift`).  
**Audit**: Tamper-evident SHA-256 cryptographic audit chain (`SCHEMA_VERSION = 2.0-CANONICAL`)  
**Authority**: Strict Dual-Key Role Governance (`System Admin`, `Relationship Manager`, `Credit Analyst`, `Sanction Authority`)

---

## 1. Automated Verification & Test Integrity
- **Backend Test Suite**: **106/106 automated `pytest` tests passing** (`pytest -v`) across 16 core suites. Verifies deterministic reducing-balance capacity (`policy_min_dscr = 1.25x`), exact binding constraint resolution, RBAC isolation, and reset concurrency boundaries (`test_reset_concurrency.py`).
- **Production Browser E2E Gate**: **12/12 Playwright Chromium tests passing (`e2e/release-gate.spec.ts`)** directly against the live Vercel production frontend (`https://frontend-swart-ten-40haipc0xl.vercel.app`) and remote Neon database (`USE_LOCAL_SERVER=false`).
- **System Readiness Endpoint**: `/ready` confirms live database connectivity (`status: ready, database: connected`) and active migration head (`migration_head: 36029ce44378`).

---

## 2. The Four Canonical Evaluator Journeys
1. **Shakti Precision Components Pvt Ltd (APPROVE)**: FHI `84/100`, DSCR `2.10x`. Supportable amount computed at `₹45.00 Lakhs` under reducing-balance EMI and exact DSCR policy bounds (`binding_constraint: NONE`).
2. **NavPrerna Tech Solutions Pvt Ltd (DEFER / EVIDENCE REQUEST)**: FHI `58/100`, DSCR `1.22x` (< `1.25x` floor). Deterministically outputs `DEFER` (`ADDITIONAL_EVIDENCE_REQUIRED`) with actionable `evidence_request_note`.
3. **Rangrez Textiles Pvt Ltd (FROZEN / RECONCILIATION)**: FHI `42/100`, DSCR `1.10x`. Locked in `RECONCILIATION_REQUIRED` due to >18% GST vs Bank statement variance flagged by the automated reconciliation engine.
4. **Nirmaan Infrastructure Services Pvt Ltd (DECLINE)**: FHI `31/100`, DSCR `0.85x`. Deterministically outputs `₹0.00` capacity (`DSCR_BREACH`), protecting IDBI Bank from NPA exposure.

