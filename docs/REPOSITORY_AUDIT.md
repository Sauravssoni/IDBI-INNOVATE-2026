# Vyapar Pulse AI - Repository Audit

## Existing Architecture
- **Backend**: FastAPI with Python 3, `pydantic` for request/response validation, and a custom `CreditEngine` implementation.
- **Frontend/Prototype**: A zero-dependency `index.html` UI built with vanilla JS and CSS, using a dual-pane master-detail layout.
- **Testing**: `pytest` is configured and passes. Tests exist for API routes and engine deterministic behavior.
- **Data Persistence**: In-memory dictionaries (`CONSENTS`, `AUDIT_LOG`) are used for state. No actual database connection, ORM, or migrations are present.
- **Infrastructure**: Only a basic `Dockerfile`. No `docker-compose.yaml` with PostgreSQL configuration yet.

## Current Capabilities
- REST API for `/health`, `/api/v1/demo-cases`, `/api/v1/consents`, `/api/v1/assess`, `/api/v1/simulate`, `/api/v1/human-decisions`, and `/api/v1/audit`.
- Baseline `CreditEngine` that computes Financial Health, Data Confidence, and Resilience scores out of 100 using a deterministic weighting algorithm.
- Generates base explanations (top positive and negative drivers, bankability actions, and warnings).
- Simple stress testing capability using fixed shock factors on revenue and buyer delays.
- A functional visual prototype for demonstration.

## Test Status
- `pytest -v` runs successfully against the baseline code. 
- 5 tests pass in ~1.07s. 
- Tests verified: `test_assessment_creates_audit_lineage`, `test_human_decision_requires_reason`, `test_hidden_champion_is_not_penalized_for_missing_bureau`, `test_low_confidence_case_abstains`, and `test_stress_scenario_reduces_or_preserves_score_not_increase_materially`.
- Fast API server startup confirmed via `uvicorn`.

## Gaps Against Target Product
- **Missing Database**: The target requires PostgreSQL as the primary development database via Docker Compose, and SQLAlchemy/Alembic for migrations.
- **Missing Mock Data Adapters**: There is no ingestion layer or connected sandbox data-source records (synthetic GST, banking, UPI, EPFO, invoice, obligation adapters).
- **Missing Next.js Frontend**: The current prototype is a raw HTML file. The target requires a React/Next.js UI with TypeScript.
- **Missing Inconsistency/Risk Detection**: Basic anomaly risks are modeled statically on the `BusinessProfile` input, but dynamic evidence reconciliation is absent.
- **Missing Vertical Slices**: The deterministic demonstration personas (e.g., Shakti Precision Components with 18 months of synthetic data) are hardcoded as summarized `BusinessProfile` inputs rather than built from granular source data.
- **Missing API Routes**: Target routes like `/cases`, `/cases/[caseId]`, `/cases/[caseId]/health-card`, `/governance`, etc. require a true MVC structure.

## Security Issues
- **CORS Configuration**: The FastAPI app currently allows all origins (`allow_origins=["*"]`) which is a security risk for a production/enterprise environment.
- No authentication or authorization is implemented.
- **Secrets Management**: No `.env` loading logic is present, though an `.env.example` file exists.

## Data-Model Gaps
- Currently, the assessment uses a flat `BusinessProfile`. 
- Missing ORM schemas for `Case`, `Consent`, `DataConnection`, `SyntheticGST`, `SyntheticBankTransaction`, `SyntheticInvoice`, etc.
- Missing explicit schema definitions for granular data ingestion (which should then aggregate up to the `BusinessProfile` used by the engine).

## Recommended Migration Plan
1. **Initialize ORM**: Integrate `SQLAlchemy` and `Alembic`. Define the models for `Case`, `Consent`, `DataConnection`, and `AuditEvent`.
2. **Setup Docker Compose**: Create a `docker-compose.yml` to run a PostgreSQL instance and the FastAPI backend.
3. **Refactor Repositories**: Replace in-memory dictionaries with Database-backed repository classes while preserving the working scoring logic.
4. **Build Data Adapters**: Implement synthetic data generators for 18 months of mock GST, bank, UPI, employment, and invoice data.
5. **Implement Next.js Frontend**: Scaffold a new Next.js app in a `frontend/` directory with the required UI routes. The existing `prototype` directory will be preserved at `legacy/prototype/` and will not be deleted until the new frontend passes acceptance.
