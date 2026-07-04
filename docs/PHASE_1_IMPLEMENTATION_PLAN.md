# Phase 1 Implementation Plan

This document outlines the strict execution path for Phase 1 (Vertical Slice for Shakti Precision Components).

## A. Audit and Baseline
- Confirm current test suite and startup commands work.
- Snapshot repository status.
- Generate REPOSITORY_AUDIT.md and EVALUATION_MATRIX.md.

## B. Repository Architecture and Tooling
- Reorganize directory structure to Clean Architecture (api, core, db, schemas, domain, integrations, services).
- Establish backend tooling (Ruff, Pytest, Mypy) and frontend tooling (Next.js, TypeScript, ESLint, Prettier).
- Create root orchestration via `docker-compose.yml` and `Makefile`.

## C. Database and Migrations
- Set up PostgreSQL via Docker.
- Define SQLAlchemy 2.0 ORM models for Core entities (cases, businesses, consents, synthetic data tables, audit).
- Configure Alembic and create initial schema migrations.

## D. Deterministic Shakti Data Generator
- Build seed scripts to generate 18 months of deterministic data (GST, Bank, UPI, EPFO, Invoices, Customers, Suppliers) for Shakti Precision Components.

## E. Adapter Boundaries and Ingestion
- Create mock integration adapters for GST, AA, UPI, and EPFO.
- Implement explicit statuses (connected, failed, stale).

## F. Feature Derivation
- Extract `BusinessProfile` aggregates from the ingested synthetic data.

## G. Three Scoring Engines
- Implement calculation logic for Financial Health, Data Confidence, and Resilience scores.
- Centralize scoring thresholds in `core/constants.py` or DB-backed configuration.

## H. Decisionability Policy
- Translate scores and integrity flags into decision outcomes (`READY_FOR_REVIEW`, `CONDITIONAL_OFFER`, etc.).

## I. Evidence Lineage
- Tie every calculated reason code back to specific synthetic evidence rows.

## J. Stress Engine
- Apply deterministic shocks (revenue decline, payment delay) and recalculate DSCR, liquidity, and resilience.

## K. Offer Engine
- Generate Conservative, Balanced, and Growth offers dynamically based on the stressed case logic.

## L. Human Decision and Audit
- Expose secure API endpoints for human approvals and logging to the tamper-evident audit table.

## M. Typed API Contracts
- Finalize Pydantic models mapping ORM entities and routing logic.

## N. Premium Application Shell
- Initialize Next.js app in `frontend/`.
- Build the global sidebar, top navigation, search, and "Synthetic Sandbox" markers using deep teal/green brand colors.

## O. Case Workflow Screens
- Build routes: `/cases/[caseId]/health-card`, `/cases/[caseId]/evidence`, `/cases/[caseId]/stress-lab`, `/cases/[caseId]/offers`, `/cases/[caseId]/decision`.
- Implement Evidence Drawer interaction for reason codes.

## P. Governance and Integrations Screens
- Build screens for global audit logs and sandbox adapter statuses.

## Q. Testing and Security Hardening
- Complete CI pipelines, write safety tests validating bounds/monotonicity, and perform security scanning (Bandit, Secret scan).

## R. Documentation and Screenshots
- Add final ADRs, update README with quickstart/screenshots, complete SECURITY_ARCHITECTURE.md.

## S. Full Clean-Environment Acceptance Run
- Verify `make setup` and `make demo` produce the complete, expected vertical slice.
