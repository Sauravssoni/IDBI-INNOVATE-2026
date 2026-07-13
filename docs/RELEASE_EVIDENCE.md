# Release Evidence

## Final Source SHA
`b77ecdda757db86c0edd188ad29aa88b46fb5db4`

## Frontend Deployed SHA
`b77ecdda757db86c0edd188ad29aa88b46fb5db4`

## Backend Deployed SHA
`b77ecdda757db86c0edd188ad29aa88b46fb5db4`

## Test Commands and Actual Test Results
Tests were executed using:
```bash
npm run test:e2e:prod
```
- Playwright E2E tests: Passing against deployed environment.
- Backend tests (`pytest`): 108 passed, 31 warnings in ~27s
- Frontend tests (`vitest`): 5 test files passed, 29 tests passed in ~10s

## Live URLs
- Frontend: https://frontend-swart-ten-40haipc0xl.vercel.app
- Backend: https://vyapar-pulse-backend.vercel.app
- Swagger: https://vyapar-pulse-backend.vercel.app/docs

## Four-persona Results
- Shakti: Evaluated limit bridge, stress testing, manual sanction controls, and package generation.
- Navprerna: Returned INSUFFICIENT_TO_ASSESS with no positive offer and ADDITIONAL_EVIDENCE_REQUIRED recommendation.
- Rangrez: Displayed reconciliation/integrity issue; routed to review without unsafe auto-approval.
- Nirmaan: Negative cash condition visible, decline recommendation shown, no positive offer.

## Package Verification Result
Decision Package seal HASH VERIFIED.

## Independent Replay Result
Decision Package INDEPENDENT REPLAY MATCHED.

## Mobile Result
At 390px, no horizontal page overflow. Navigation remains usable, summary cards readable, human sanction controls usable, and verify/replay controls usable.

## Known Limitations
- The system is a deterministic prototype for submission and evaluation, not regulator-certified, bank-certified, or production-approved.
