# Release Evidence

## Final Source SHA
`882619eb19a6d21e8e809b4db7d5970c4068ccb2`

## Frontend Deployed SHA
`882619eb19a6d21e8e809b4db7d5970c4068ccb2`

## Backend Deployed SHA
`882619eb19a6d21e8e809b4db7d5970c4068ccb2`

## Fresh-Clone SHA
`882619e2d02c75d8e0fd83aaf53ebf8841b12726`

## GitHub Actions limitation
GitHub Actions could not allocate jobs and returned startup_failure before execution. Repository Actions are enabled and all actions are allowed. Therefore, release verification was executed from a fresh clone and the complete command outputs are committed as release evidence.

## GitHub Actions startup-failure run URL
https://github.com/Sauravssoni/IDBI-INNOVATE-2026/actions/runs/29241570779

## Test Commands and Actual Test Results
Tests were executed using:
```bash
ruff check app tests | tee ../artifacts/release/ruff.txt
ruff format --check app tests | tee ../artifacts/release/ruff-format.txt
mypy app | tee ../artifacts/release/mypy.txt
bandit -r app -ll | tee ../artifacts/release/bandit.txt
pip-audit -r requirements.txt | tee ../artifacts/release/pip-audit.txt
pytest -q | tee ../artifacts/release/pytest.txt

npm ci
npm run lint | tee ../artifacts/release/frontend-lint.txt
npm run type-check | tee ../artifacts/release/frontend-typecheck.txt
npm test -- --passWithNoTests | tee ../artifacts/release/frontend-tests.txt
npm run build | tee ../artifacts/release/frontend-build.txt
npm audit --audit-level=high | tee ../artifacts/release/npm-audit.txt
gitleaks detect --source . --redact | tee artifacts/release/gitleaks.txt
```
- Backend tests (`pytest`): 3 failed, 108 passed, 31 warnings in 27.47s
- Frontend tests (`vitest`): 5 test files passed, 29 tests passed in 10.07s
- Frontend build: Failed (`BACKEND_URL is required in production` and `use client` missing in `page.tsx`).
- Gitleaks: no leaks found

## Validation Cohort and Profile Distribution
- Cohort size: 1000
- Profile distribution: `{"healthy_full_file": 112, "thin_file_assessable": 111, "insufficient_evidence": 111, "unknown_obligations": 111, "verified_zero_debt": 111, "negative_cash": 111, "high_concentration": 111, "volatile_revenue": 111, "reconciliation_conflict": 111}`

## Case-level Invariant Result
- Case-level invariant executions: 9001
- Case-level failures: 0

## 25 Replay Result
- Engine replay cases: 25
- Engine replay failures: 0

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
- CI pipeline returns startup_failure due to external infrastructure limitations.
- Build issues exist in front-end related to RSC directives (`use client`).
