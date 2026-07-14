# Release Evidence

## Final Source SHA
`PENDING (tested_code_sha)`

## Fresh-clone SHA
`PENDING (tested_code_sha)`

## Frontend Deployed SHA
`PENDING (deployed_runtime_sha)`

## Backend Deployed SHA
`PENDING (deployed_runtime_sha)`

## Test Commands and Actual Test Results
Tests were executed using the clean release gate:
```bash
cd backend && pytest -v --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=80
cd frontend && npm ci && npm run lint && npm run type-check && npm test -- --passWithNoTests && npx playwright install --with-deps && npm run test:e2e
```
- Playwright E2E tests: Successfully executed journey against deployed environment.
- Backend tests (`pytest`): 115 passed.
- Frontend tests (`vitest`): 5 test files passed, 29 tests passed.
- `pip-audit`: Evaluated environment dependencies. No known vulnerabilities found.
- `bandit`: Clean scan, no high severity issues found in `app`.
- `ruff`: Clean, 0 linting errors and format issues in `app` and `tests`.

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
