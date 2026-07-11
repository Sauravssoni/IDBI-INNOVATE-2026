# Vyapar Pulse — Evidence-to-Sanction Deterministic Credit Twin Prototype

![Hero Screenshot](docs/assets/screenshots/01-demo-access.png)

**An evidence-to-sanction deterministic credit twin prototype for Indian MSME working capital assessment.**

---

## 1. Value Proposition & Deterministic Architecture
Vyapar Pulse eliminates black-box AI risk in MSME lending. Instead of relying on opaque LLM scoring, it mathematically normalizes multi-rail evidence (GST returns, Bank Statements, Invoices, Bureau data) into a deterministic `Credit Twin` vector. It executes strictly versioned financial math (6-Pillar Structural Scoring, `SafeLimitEngine` exact reducing-balance amortization, and DSCR rules) and enforces a human-in-the-loop sanction workflow where AI explains and organizes, but deterministic policy engines and human authorities control decisions.

---

## 1.1 The 500-MSME Inclusion Impact
We deterministically simulated 500 Indian MSMEs across tiers and segments against our 6-Pillar scoring engine. 
- **Traditional Model Unassessed/Rejected**: 356 MSMEs
- **Vyapar Pulse Included**: 273 MSMEs (76.7% Inclusion Rate)
- **Credit Unlocked**: ₹ 118+ Crores
*See `artifacts/inclusion_impact_report.json` for full breakdown.*

---

## 2. Public Demo & Verification Access
- **Frontend URL**: Proxied Next.js frontend running locally on port `3005` or via cloud deployment.
- **Backend API Docs**: `/docs` OpenAPI interface.
- **System Readiness Endpoint**: `/ready` verifying live database connectivity and schema compatibility.
- **Health Check Endpoint**: `/health` verifying service heartbeat.

---

## 3. Judge This in Three Minutes (Step-by-Step Evaluation)
1. **Demo Reset**: Click **Demo Reset** (`/api/demo/reset`) to seed exactly four canonical deterministic MSME personas.
2. **Analyst Login**: Select **Credit Analyst** role (`credit@bank.example`).
3. **Inspect Shakti Precision Components**: View multi-rail evidence, reconcile GST turnover vs. bank credits, and generate the deterministic `Credit Twin`.
4. **Inspect Decision Package & Evidence Passport**: Review the `Decision Package` featuring a cryptographic `package_hash` (SHA-256), the `Evidence Sufficiency Passport` (`EVD-001`) with exponential freshness decay (`decay_score = 100 * e^(-0.015*t)`), and authoritative evidence linkage.
5. **Analyze Stress Lab & Bankability Path**: Open the **Decision Sensitivity Lab** (`STR-001`) to test revenue/margin shocks, and the **Bankability Path Engine** (`BNK-001`) for 30/60/90-day intervention roadmaps.
6. **Submit Recommendation**: Recommend an alternative facility structure (`CONDITIONAL_OFFER`).
7. **Sanction Authority Review**: Switch role to **Sanctioning Authority** (`sa@bank.example`) to inspect the proposal and issue final human sanction.

---

## 4. Four Canonical MSME Personas
1. **Shakti Precision Components Pvt Ltd** (Manufacturing — Auto Ancillary, Working Capital Line):
   - Requested: ₹50.00 Lakh
   - Supportable Limit: ₹35.69 Lakh (constrained by exact reducing-balance EMI and DSCR floor ≥ 1.15)
   - Outcome: `CONDITIONAL_OFFER` (requires alternative facility structuring).
2. **Navprerna Tech Solutions Pvt Ltd** (Services — IT & Cloud Architecture):
   - Outcome: `ADDITIONAL_EVIDENCE_REQUIRED` due to missing recent GST filings and stale bank statements.
3. **Rangrez Textiles Pvt Ltd** (Manufacturing — Apparel & Garments):
   - Outcome: `READY_FOR_REVIEW` / `DECLINE_RECOMMENDED` due to severe cash flow contraction and over-leverage.
4. **Nirmaan Infrastructure Services Pvt Ltd** (Construction — Civil & Electrical Infrastructure):
   - Outcome: `DECLINE_RECOMMENDED` due to negative operating cash flows and elevated debt service obligations.

---

## 5. Decision Package & Evidence Sufficiency Passport (`EVD-001`/`EVD-002`)
Every evaluation produces a deterministic `DecisionPackageResponse` that embeds:
- **Evidence Sufficiency Passport**: Quantitative scoring of evidence depth and multi-rail coverage across Banking, GST, Bureau, and Financial statements.
- **Freshness Decay Math**: Exponential time-decay model (`100 * e^(-0.015*t)`) penalizing stale filings (>30 days).
- **Authoritative Evidence IDs**: Explicit UUID references binding every calculation input directly to raw ingested documents (`authoritative_evidence_ids`).
- **Reducing-Balance DSCR**: Exact formula `P * r * (1+r)^n / ((1+r)^n - 1)` calculating post-loan DSCR against proposed limits.

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

## 8. System Architecture
- **Frontend**: Next.js 14, Tailwind CSS, Playwright E2E verification.
- **Backend API**: Python 3.10+, FastAPI, Pydantic v2.
- **Database & ORM**: PostgreSQL with SQLAlchemy 2.0+ and explicit table-level row locks (`FOR UPDATE`) and `expected_version` checks for Compare-And-Swap (CAS).
- **Verification Suite**: 70+ domain/API/BOLA pytest cases, 18 Decision Assurance assertions, and 12-step E2E Demo Walkthrough.

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
- **Replay Verification**: Proves identical responses under network retry conditions.

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
*Authored by Syntheon Technology Private Limited for the IDBI Innovate 2026 Track 03 Competition Dominance RC3.*
