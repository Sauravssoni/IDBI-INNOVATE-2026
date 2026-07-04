# Implementation Status: Phase 1.1 Evidence Gate

## 1. Documentation Quality Gates
- **Status:** PARTIALLY_IMPLEMENTED
- **Source Files:** `docs/`, `scripts/docs_check.sh`
- **Tests:** `make docs-check` only runs partial grep checks. Full markdownlint, link validation, and OpenAPI freshness are pending.

## 2. Clean-Room Verification (Quality Gates)
- **Status:** PARTIALLY_IMPLEMENTED
- **Source Files:** `frontend/package.json`, `backend/Makefile`, `backend/pytest.ini`
- **Tests:** Basic typecheck, tests, security scans, and build pass locally. Full CI integration blocked.

## 3. Separation of System vs. Human Decision
- **Status:** IMPLEMENTED_AND_TESTED
- **Source Files:** `backend/app/db/orm/cases.py`, `backend/app/api/routers/cases.py`, `backend/app/engine.py`

## 4. Security Controls
- **CSRF Protection:** NOT_IMPLEMENTED
- **Case-level object authorisation:** NOT_IMPLEMENTED
- **Real idempotency:** NOT_IMPLEMENTED
- **Compare-and-swap concurrency control:** NOT_IMPLEMENTED
- **Atomic decision plus audit write:** NOT_IMPLEMENTED
- **Hashed session-token storage:** NOT_IMPLEMENTED
- **Session rotation/revocation:** PARTIALLY_IMPLEMENTED
- **DAST:** NOT_IMPLEMENTED
- **Full security scanner suite:** PARTIALLY_IMPLEMENTED

## 5. Domain Calculations
- **Product-calculated offer metrics:** PARTIALLY_IMPLEMENTED (Uses placeholders instead of strict product strategies for Repayment, DSCR, and Liquidity impact).

## 6. GitHub CI / Governance
- **Status:** BLOCKED
- **Source Files:** `.github/workflows/quality_gate.yml`
- **Note:** GitHub Actions blocked/failed to provision on the repository. CI script relies on missing `backend/requirements-dev.txt`.
