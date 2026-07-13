# Release Evidence

## Final Source SHA
`5478d6a198a857d02c75ff455a72e11b16fc3a98`

## Fresh-clone SHA
`5478d6a198a857d02c75ff455a72e11b16fc3a98`

## Frontend Deployed SHA
`5478d6a198a857d02c75ff455a72e11b16fc3a98`

## Backend Deployed SHA
`5478d6a198a857d02c75ff455a72e11b16fc3a98`

## Test Commands and Actual Test Results
Tests were executed using the clean release gate:
```bash
cd backend && TESTING=true python -m pytest
cd frontend && npm ci && npm run lint && npm run type-check && npm test && BACKEND_URL=https://vyapar-pulse-backend.vercel.app npm run build
```
- Playwright E2E tests: Successfully executed journey against deployed environment.
- Backend tests (`pytest`): 112 passed, 2 warnings in ~25s.
- Frontend tests (`vitest`): 5 test files passed, 29 tests passed in ~5s. Frontend build succeeded.
- `pip-audit`: Evaluated environment dependencies. Identified unresolved known CVEs in 35+ data science and utility libraries (e.g., `torch`, `transformers`, `nltk`, `lxml`, `python-jose`). **Accepted Limitation:** These dependencies are maintained for AI/OCR feature readiness and are isolated from untrusted serialized payload ingestion at runtime.
- `bandit`: Clean scan, no high severity issues found in `app`.
- `ruff`: Clean, 0 linting errors and format issues in `app`.

## Live URLs
- Frontend: https://frontend-swart-ten-40haipc0xl.vercel.app
- Backend: https://vyapar-pulse-backend.vercel.app
- Swagger: https://vyapar-pulse-backend.vercel.app/docs

## Four-persona Results
- Shakti (SHAKTI_PRECISION_001): Evaluated limit bridge, stress testing, manual sanction controls, and package generation.
- Navprerna (NAVPRERNA_TECH_001): Returned INSUFFICIENT_TO_ASSESS with no positive offer and ADDITIONAL_EVIDENCE_REQUIRED recommendation.
- Rangrez (RANGREZ_TEXTILES_001): Displayed reconciliation/integrity issue; routed to review without unsafe auto-approval.
- Nirmaan (NIRMAAN_INFRA_001): Negative cash condition visible, decline recommendation shown, no positive offer.

## Package Verification Result
Decision Package seal HASH VERIFIED. Only `SANCTIONING_AUTHORITY` successfully seals the final decision.
Offline seal attempts correctly fail-closed.
Real `package_id` generated successfully upon final explicit seal.

## Independent Replay Result
Decision Package INDEPENDENT REPLAY MATCHED.

## Mobile Result
At 390px, no horizontal page overflow. Navigation remains usable, summary cards readable, human sanction controls usable, and verify/replay controls usable.

## Known Limitations
- The system is a deterministic prototype for submission and evaluation, not regulator-certified, bank-certified, or production-approved.
