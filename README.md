# Vyapar Pulse

**The most advanced, true MSME sanctioning engine.**

*Release Tag: `v1.3.3-idbi-winning-candidate`*

## Overview

Vyapar Pulse is an authoritative, end-to-end MSME credit decision engine and borrower portal built for the IDBI Innovate 2026 Track 03 Competition. Rather than presenting static scorecards or fabricated outputs, Vyapar Pulse dynamically computes deterministic limits and limits across multiple loan products using rigorous mathematical cash-flow analysis.

### Core Capabilities

- **8-Section Decision Room:** A fully implemented, step-by-step state machine ensuring rigid, ordered progression from initialization, KYC, financial capacity evaluation, through to analyst recommendation and final Sanctioning Authority (SA) decision.
- **Canonical Limit Bridge:** The engine dynamically models constraints via a multi-stage limit bridge (Requested Amount -> Cash Serviceability Cap -> Verified Obligation Cap) across four distinct products: Working Capital Line, Receivables Finance, Term Loan, and Equipment Finance.
- **Evidence-Conditioned Scoring:** Credit scores and capacities are directly bounded by verified evidence (Bank, Bureau, GST). 
- **Borrower-Safe Applicant Portal:** A sanitized, real-time frontend for borrowers, offering actionable "Bankability" interventions without leaking internal bank policy data.
- **Stress & Reverse Stress Testing:** Simulates shocks to revenue and costs, outputting exact DSCR impact and breaking points (where DSCR hits 1.0x).
- **Independent Invariant Validation:** Mathematical validation across 1,000 deterministic synthetic cases, asserting that final limits never exceed logical policy or mathematical bounds.

## Technical Architecture

- **Backend:** Python / FastAPI. Uses Pydantic for strict API typing and dependency injection for robust data flow.
- **Frontend:** Next.js (React) / TypeScript / Tailwind CSS. Features dynamic, real-time sync with backend endpoints and rich data visualization.
- **Database Architecture (Conceptual):** Implements `expected_version` concurrency control (Compare-And-Swap) and idempotency keys to guarantee transaction integrity, simulating a robust multi-AZ PostgreSQL deployment.
- **Continuous Integration (CI):** Fully configured GitHub Actions workflow (`quality_gate.yml`) ensuring type safety, testing with coverage, linting, and formatting checks on all commits.

## Running Locally

1. **Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Validation:**
   ```bash
   python3 scripts/generate_portfolio_assurance.py
   python3 backend/app/validation/invariant_checker.py
   ```

---
*Authored for the IDBI Innovate 2026 Track 03 Competition Dominance Submission (`v1.3.3-idbi-winning-candidate`).*
