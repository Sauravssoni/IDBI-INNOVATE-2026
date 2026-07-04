# Vyapar Pulse AI - Evaluation Matrix

This matrix maps banking and judging dimensions to repository evidence to ensure continuous auditability.

| Dimension | Requirement | Implementation Strategy | File/Module | Test or Proof | Demo Screen | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Problem Relevance** | Credit-invisible MSME assessment | Implement synthetic data generators mapping alternative data to financial health. | `app/feature_derivation.py` | Persona tests for hidden champions | `/cases/[id]/health-card` | PENDING |
| **Innovation** | Non-LLM deterministic credit twin | Distinct Financial Health and Data Confidence scores. | `app/domain/scoring/` | `test_safety.py` (monotonicity) | `/cases/[id]/stress-lab` | PENDING |
| **Functional Completeness** | End-to-end assessment flow | UI, Backend API, PostgreSQL DB, robust ORM. | `app/api/routers/assessments.py` | E2E vertical slice test | Dashboard & Cases | PENDING |
| **Banking Usability** | Role-centric premium UI | Next.js tailored UI with strict banking design tokens. | `frontend/app/` | Cypress/Component tests | All Screens | PENDING |
| **Technical Architecture** | Clean, layered architecture | Separate API, ORM, schemas, and domain scoring rules. | `backend/app/` | Architectural linters | N/A | PENDING |
| **Security and Privacy** | Defence-in-depth, RBAC | JWT/Auth abstraction, CORS, DB constraints, audit logging. | `app/core/security.py` | Auth and permission tests | N/A | PENDING |
| **Explainability** | Grounded reason codes | Evidence lineage linking scores to raw transaction rows. | `app/domain/explanations/` | Reason code mapping tests | Evidence Drawer | PENDING |
| **Integration Readiness** | Canonical sandbox adapters | Adapter pattern for GST, AA, UPI, EPFO with mock APIs. | `app/integrations/` | Mock adapter unit tests | `/integrations` | PENDING |
| **Scalability** | PostgreSQL & Docker | `docker-compose.yml` defining full stack, Alembic migrations. | `infra/docker-compose.yml` | Clean DB migration test | N/A | PENDING |
| **Testing** | Prove invariants | Pytest suite validating safety properties (bounds, monotonic). | `backend/tests/` | CI/CD pipeline runs | N/A | PENDING |
| **Documentation** | Evaluator-ready repository | ADRs, Architecture, PRD, Security docs in root/docs. | `docs/` | Repository linter | N/A | PENDING |
| **Deployment Readiness** | Local reproducible startup | Makefile or `docker-compose up` 1-click startup. | `Makefile` | CI integration test | N/A | PENDING |
| **UI/UX Quality** | Professional enterprise UI | Strict design constraints, empty/loading/error states. | `frontend/components/` | Accessibility & visual tests | All Screens | PENDING |
