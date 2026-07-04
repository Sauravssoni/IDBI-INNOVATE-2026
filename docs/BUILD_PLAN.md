# Vyapar Pulse AI - Build Plan

## P0 Submission Requirements (Phase 1)
- **Framework & Database**: Setup Next.js with TypeScript for the frontend, integrate `SQLAlchemy` with PostgreSQL (via Docker Compose) and `Alembic` for migrations.
- **Vertical Slice (Shakti Precision Components)**: 
  - Complete backend models for `Case`, `Consent`, `DataConnection`, `SyntheticGST`, `SyntheticBankTransaction`, `SyntheticInvoice`, and `AuditEvent`.
  - Synthetic Data Generators providing 18 months of deterministic mock data for Shakti Precision Components.
  - Feature Derivation layer that transforms granular data into the `BusinessProfile` consumed by the `CreditEngine`.
- **Core Engine & Safety**: 
  - Expose API endpoints for base assessments, stress simulations, and human decisions.
  - Write safety test suite proving the engine respects boundaries (scores 0-100, shocks behave monotonically, etc).
- **Frontend / UI**:
  - Implement a professional enterprise UI with routes for Dashboard, Case Queue, Case Detail, Financial Health Card, Evidence Drill-down, Stress Lab, Offers, Decision, Governance, and Audit.
  - The UI must use the specified theme (deep teal/green, white, saffron/orange) and properly display "Synthetic Sandbox Data" labels.

## P1 Enhancements
- **Remaining Personas**: Implement granular synthetic data pipelines and deterministic rendering for the remaining three mandatory personas (NavPrerna Business Services, Rangrez Festive Retail, Aarohan Trading Network).
- **Integrity Risk Detection Engine**: Advanced inconsistency checks (e.g., duplicate invoices, circular flows, mismatched turnover) mapped into the anomaly score.
- **Explainability API**: Generative or deterministic grounded explanations linking reason codes to the raw transaction/invoice rows.

## Deferred Roadmap
- Real Third-Party API integrations (Account Aggregator, GSTN, EPFO).
- Complex LLM-based navigation (e.g., natural language querying over the audit log or evidence set).
- Advanced production multi-tenant deployment architecture.

## Dependency Order
1. **Infrastructure**: PostgreSQL + Docker Compose setup.
2. **Database Layer**: SQLAlchemy Models + Alembic migrations.
3. **Data Ingestion**: Synthetic data generation scripts and loaders.
4. **API Layer**: Update FastAPI routes to interact with the database instead of in-memory stores.
5. **Frontend Application**: Scaffold Next.js app, configure routing, theme, and API client.
6. **Integration**: Connect Next.js views to FastAPI backend and verify vertical slice.

## Acceptance Criteria
- All frontend routes load without errors and reflect the deep teal/green enterprise UI direction.
- The `Shakti Precision Components` case correctly loads from generated synthetic data, passes through the feature derivation, and accurately displays scores.
- Safety tests pass locally via `pytest` (asserting monotonicity and boundary conditions).
- Running `docker-compose up` successfully starts both the database and the backend service.
- The audit log faithfully records assessments and simulated human decisions securely.

## Risks and Mitigations
- **Risk**: Complexity of building deterministic synthetic data that correctly yields the exact required `BusinessProfile` aggregates.
  - *Mitigation*: Start with static data seeds. Generate transactions with a fixed random seed to ensure re-runs yield identical features.
- **Risk**: Tight UI delivery timelines.
  - *Mitigation*: Use a robust component library (e.g. Tailwind CSS, shadcn/ui or simple vanilla CSS with standard patterns) and avoid complex micro-animations. Focus on data presentation and layout.
- **Risk**: Sync issues between database schema and Pydantic models.
  - *Mitigation*: Strictly use SQLAlchemy ORM models, mapped seamlessly to Pydantic schemas, and enforce `Alembic` for any iterative changes.
