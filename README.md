# Vyapar Pulse

Vyapar Pulse is an evidence-linked MSME credit assessment engine designed for the Indian context.
It replaces manual reconciliation by generating a deterministic **MSME Credit Twin** from verified GST and bank statement data. 
The system leverages a multi-layer architecture:
*   **Next.js Frontend:** A clean, brand-aligned UI with a 6-step guided evaluation sandbox for live demonstrations.
*   **FastAPI Backend:** Orchestrates case data, external API ingestion, and evidence gathering via REST endpoints.
*   **PostgreSQL & SQLAlchemy Models:** Enforces strict state machines (CaseStatus), RBAC (SanctioningMandate), and Object-Level Authorization (BOLA).
*   **Idempotency & Cryptographic Audit:** Uses SHA-256 hash-linking and exact version tracking to assure tamper-evident workflows and prevent double-execution.
*   **Multi-Agent Mock Integrations:** Connects robust deterministic seeded data representing complex integrations with core banking and GST networks.

## Quick Start (Local Docker)

The repository is fully containerized and controlled via `make`.

1. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```

2. **Boot the Demo Environment:**
   ```bash
   make demo-up
   ```
   *   **Frontend:** http://localhost:3005
   *   **Backend API Docs:** http://localhost:8000/docs

3. **Verify Assurance & Business Logic:**
   ```bash
   make verify
   ```

## Evaluator Disclosures

This repository is submitted as a prototype for **IDBI Innovate 2026**.
All data is synthetic and decisioning is strictly deterministic. The system operates on a rigorous Compare-And-Swap (CAS) locking mechanism to produce a mathematically assured audit ledger.
