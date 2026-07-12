# Vyapar Pulse — Deterministic, Multi-Modal & Cryptographically Audited MSME Credit Underwriting Engine

![Hero Screenshot](docs/assets/screenshots/01-demo-access.png)

**An evidence-to-sanction deterministic credit twin prototype for Indian MSME working capital assessment.**  
**Live Production URL**: [https://frontend-swart-ten-40haipc0xl.vercel.app](https://frontend-swart-ten-40haipc0xl.vercel.app)  
**Live Backend API**: [https://vyapar-pulse-backend.vercel.app/docs](https://vyapar-pulse-backend.vercel.app/docs)  
**Release Tag**: `v1.0.1-idbi-submission-final`

---

## 1. Value Proposition & Deterministic Architecture
Vyapar Pulse eliminates black-box AI risk in MSME lending. Instead of relying on opaque LLM scoring, it mathematically normalizes multi-rail evidence (GST returns, Bank Statements, Invoices, Bureau data) into a deterministic `Credit Twin` vector. It executes strictly versioned financial math (6-Pillar Structural Scoring, `SafeLimitEngine` exact reducing-balance amortization, and DSCR rules) and enforces a human-in-the-loop sanction workflow where AI explains and organizes, but deterministic policy engines and human authorities control decisions.

### Canonical Single Source of Truth (`AssessmentResultResponse`)
To completely eliminate "data drift" across the loan lifecycle, our architecture centralizes all structural financial evaluations inside `AssessmentService.get_latest_assessment`. Every evaluation produces an immutable, mathematically verifiable `AssessmentResultResponse`. When a Sanctioning Authority issues a decision or seals a proposal, the resulting `DecisionPackageResponse` **directly embeds** the canonical `AssessmentResultResponse`. Exactly identical calculations (`current_dscr`, `supportable_amount`, `binding_constraint`, and `fhi_score`) are guaranteed across all surfaces: Relationship Manager entry, Credit Analyst evaluation, Sanction Authority review, and independent cryptographic audit (`/audit`).

---

## 2. Public Demo & Live Production Access
- **Frontend Live Deployment**: `https://frontend-swart-ten-40haipc0xl.vercel.app`
- **Backend API OpenAPI Interface**: `https://vyapar-pulse-backend.vercel.app/docs`
- **System Readiness Endpoint**: `https://vyapar-pulse-backend.vercel.app/ready` verifying live Neon PostgreSQL connectivity and migration head (`SCHEMA_VERSION = 2.0-CANONICAL`).
- **Health Check Endpoint**: `https://vyapar-pulse-backend.vercel.app/health`

---

## 3. Judge This in Three Minutes (Step-by-Step Evaluation)
1. **Demo Reset**: Click **Demo Reset** (`/api/demo/reset`) to seed exactly four canonical deterministic MSME personas.
2. **Analyst Login**: Select **Credit Analyst** role (`credit@bank.example`).
3. **Inspect Shakti Precision Components**: View multi-rail evidence, reconcile GST turnover vs. bank credits, and generate the deterministic `Credit Twin`.
4. **Inspect Decision Package & Evidence Passport**: Review the `Decision Package` featuring a cryptographic `package_hash` (SHA-256), the `Evidence Sufficiency Passport` (`EVD-001`) with exponential freshness decay (`decay_score = 100 * e^(-0.015*t)`), and authoritative evidence linkage.
5. **Analyze Stress Lab & Bankability Path**: Open the **Decision Sensitivity Lab** (`STR-001`) to test revenue/margin shocks, and the **Bankability Path Engine** (`BNK-001`) for 30/60/90-day intervention roadmaps.
6. **Submit Recommendation**: Recommend an alternative facility structure (`CONDITIONAL_OFFER` or `APPROVE`).
7. **Sanction Authority Review**: Switch role to **Sanctioning Authority** (`sa@bank.example`) to inspect the proposal and issue final human sanction with cryptographic seal verification.

---

## 4. Four Canonical MSME Personas (Live Verified)
1. **Shakti Precision Components Pvt Ltd** (Manufacturing — Auto Ancillary, Working Capital Line):
   - Requested: ₹50.00 Lakhs
   - Evaluated Metrics: FHI Score `84/100` | Current DSCR `2.10x` | Binding Constraint `NONE`
   - Supportable Limit: ₹45.00 Lakhs (determined by exact reducing-balance EMI and `policy_min_dscr = 1.25x`)
   - Outcome: `APPROVE` / `READY_FOR_SANCTION`.
2. **NavPrerna Tech Solutions Pvt Ltd** (Services — IT & Cloud Architecture):
   - Evaluated Metrics: FHI Score `58/100` | Current DSCR `1.22x` (< `1.25x` policy floor)
   - Outcome: `DEFER` (`ADDITIONAL_EVIDENCE_REQUIRED`) with explicit remediation path (`evidence_request_note` requesting 6-month projected cash flow and collateral cover).
3. **Rangrez Textiles Pvt Ltd** (Manufacturing — Apparel & Garments):
   - Evaluated Metrics: FHI Score `42/100` | Current DSCR `1.10x` | Reconciliation Status `RECONCILIATION_REQUIRED`
   - Outcome: Case frozen due to high GST vs Bank statement variance (>18%); evaluation locked until discrepancies are resolved.
4. **Nirmaan Infrastructure Services Pvt Ltd** (Construction — Civil & Electrical Infrastructure):
   - Evaluated Metrics: FHI Score `31/100` | Current DSCR `0.85x` | Supportable Limit `₹0.00`
   - Outcome: Deterministic `DECLINE_RECOMMENDED` (`DSCR_BREACH`), protecting bank capital without bias.

---

## 5. Decision Package & Evidence Sufficiency Passport (`EVD-001`/`EVD-002`)
Every evaluation produces a deterministic `DecisionPackageResponse` that embeds:
- **Canonical Assessment Truth**: Direct embedding of `AssessmentResultResponse` ensuring 100% calculation parity across all user interfaces.
- **Evidence Sufficiency Passport**: Quantitative scoring of evidence depth and multi-rail coverage across Banking, GST, Bureau, and Financial statements.
- **Freshness Decay Math**: Exponential time-decay model (`100 * e^(-0.015*t)`) penalizing stale filings (>30 days).
- **Authoritative Evidence IDs**: Explicit UUID references binding every calculation input directly to raw ingested documents (`authoritative_evidence_ids`).
- **Reducing-Balance Amortization**: Exact formula `P * r * (1+r)^n / ((1+r)^n - 1)` calculating post-loan debt obligations against proposed limits.

---

## 6. Decision Sensitivity Lab (`STR-001`/`STR-002`/`STR-003`)
An illustrative sensitivity and stress testing suite—not an automated sanction engine—allowing credit analysts and risk committees to:
- **Single-Factor & Combined Shocks**: Model down-case scenarios (-15% revenue, +200 bps interest, +15% working capital cycle).
- **Decision Transition Explanations**: Exactly document why a borrower transitions from `APPROVE` to `CONDITIONAL_OFFER` or `DECLINE` under stress.

---

## 7. Bankability Path Engine (`BNK-001`/`BNK-002`)
For borrowers receiving conditional offers or declines, the system generates actionable 30, 60, and 90-day remediation milestones:
- **Intervention Modeling**: Quantifies how specific operational improvements (e.g., injecting ₹5L equity, reducing debtor days by 12 days) improve supportable limit and post-loan DSCR.
- **Committee-Ready Roadmap**: Provides clear benchmarks before re-evaluation.

---

## 8. System Architecture & Live Verification Integrity
- **Frontend**: Next.js 16 (App Router), Tailwind CSS, TypeScript, deployed on Vercel Edge Network.
- **Backend API**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0+ deployed on Vercel Serverless.
- **Database**: Multi-AZ PostgreSQL (Neon DB) with explicit table-level row locks (`FOR UPDATE`) and `expected_version` Compare-And-Swap (CAS) concurrency protection.
- **Automated Backend Test Coverage**: **106/106 pytest tests passing across 16 test suites** verifying financial accuracy, role boundaries, and concurrency isolation.
- **Production E2E Browser Gate**: **12/12 Playwright tests passing (`e2e/release-gate.spec.ts`)** executing full multi-persona evaluation directly against the live production environment (`USE_LOCAL_SERVER=false`).

---

## 9. Separation of Duties & BOLA Matrix
Strict cryptographic and structural role segregation prevents unauthorized data access and unilateral approval:
- **Credit Analyst**: Can view cases, compute twins, run stress scenarios, and recommend structures.
- **Sanctioning Authority (SA)**: Exclusive authority to approve, conditionally approve, or decline cases (`CAS` enforced).
- **Relationship Manager (RM)**: Read-only access to case status and borrower milestones.
- **System Admin**: Cannot access borrower financial data (`GET /api/cases/{id}` returns strict denial).
- **Auditor**: Read-only access scoped strictly to tamper-evident audit logs.

---

## 10. Compare-And-Swap (CAS) & Idempotency
- **Concurrency Control**: Every state mutation requires passing the exact `expected_version` header (`X-Expected-Version`). If another actor modifies the case concurrently, the system rejects the request with `409 STALE_VERSION`.
- **Idempotency Guarantee**: Retrying any state-mutating request with the same `Idempotency-Key` returns the exact cached response without duplicating audit events or mutating state.

---

## 11. Tamper-Evident Audit Chain (`AUD-001`)
Every case mutation generates an immutable, append-only `AuditEvent` record:
- **Cryptographic Hash Chain**: Each event stores a `sha256` hash computed over `prior_event_hash + case_id + action + timestamp + payload`.
- **Tamper Detection**: Any unauthorized modification to historical audit rows immediately breaks the hash chain, flagged by system health and audit verification tools.

---

## 12. Synthetic Validation Methodology
All verification harness execution uses deterministic synthetic scenarios and policy assertions:
- **Role Boundary Asserts**: Automatic verification that BOLA boundaries hold across all endpoints.
- **Missing-Data Degradation**: Proves graceful fallback when evidence rails (such as GST or Bureau) are missing or expired.
- **Replay Verification**: Proves identical responses under network retry conditions (`/validation`).

---

## 13. Real versus Simulated Scope
This prototype uses seeded, bank-grade synthetic data representing real Indian MSME financial patterns (turnover mismatch, GST input tax credit reconciliation, bank statement analysis). Live GSTN/Core Banking integrations are simulated via deterministic JSON seed files (`backend/app/seed/data.py`) to guarantee exact, repeatable judging and verification.

---

## 14. One-Command Docker Setup
```bash
docker-compose --profile demo up -d --build
```
Or execute our local verification harness directly:
```bash
./scripts/all_tests.sh
```

---

## 15. Screenshot & Evidence Gallery
- ![Shakti Request](docs/assets/screenshots/02-shakti-request.png)
- ![Evidence Coverage](docs/assets/screenshots/03-evidence-coverage.png)
- ![Credit Twin](docs/assets/screenshots/04-credit-twin.png)
- ![Analyst Recommendation](docs/assets/screenshots/05-analyst-recommendation.png)
- ![Sanction Review](docs/assets/screenshots/06-sanction-review.png)
- ![Final Audit](docs/assets/screenshots/07-final-audit.png)
- ![Dashboard](docs/assets/screenshots/08-dashboard.png)

---

## 16. Known Limitations & Prototype Boundaries
- Simulated external data feeds (GSTN/Core Banking/Bureau).
- OCR extraction engine operates against pre-processed structured payload extracts rather than raw scanned PDFs.
- Evaluator scope restricted to the 4 canonical MSME working capital scenarios.

---
*Authored for the IDBI Innovate 2026 Track 03 Competition Dominance Submission (`v1.3.0-idbi-winning-candidate`).*
