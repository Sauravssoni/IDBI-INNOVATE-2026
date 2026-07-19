# Vyapar Pulse — Submission Proof and IDBI Pilot Pack

> Judge-facing navigation document. This file consolidates evidence already present in the repository and verified release; it does not add product capabilities or modify the frozen deployment.

## 1. What Vyapar Pulse proves

A conventional score estimates risk. Vyapar Pulse governs the complete lending decision around that score:

1. Was sufficient, reconcilable evidence available?
2. What amount can the MSME safely service under baseline and adverse conditions?
3. Which officer may recommend, sanction, verify or audit the case?
4. Was the final decision package altered after approval?
5. Can the exact historical decision be independently recomputed later?

The product is intentionally model-agnostic. IDBI may retain, replace or recalibrate the Financial Health Score or PD model while preserving the evidence, capacity, maker-checker, sealing and replay controls around it.

## 2. Canonical release lineage

| Record | Verified value |
|---|---|
| Frozen production source | `21e83d270508d4d95f016f7ad1d1ee2f523ac181` |
| Release-evidence commit | `2c9b510a8be2b7a4185671c3e785d864243c0fef` |
| Immutable release tag | `v1.3.12-idbi-final` |
| Backend verification | `116 passed` |
| Frontend verification | `29 passed` |
| Deterministic assurance cohort | `1,000 / 1,000 passed` |
| Independent replay checks | `25 passed` |

The deployed frontend, deployed backend and clean release checkout are recorded against the same frozen production SHA in [`docs/RELEASE_EVIDENCE.md`](docs/RELEASE_EVIDENCE.md). Later `main` commits are judge-navigation documentation only; they do not alter the frozen product or release tag.

## 3. Three-minute judge route

- Watch the [final demo video](https://drive.google.com/file/d/1io4_vgZD4rxJGTCxyfSXwrNyHEbiVFOT/view?usp=sharing).
- Open the [live product](https://frontend-swart-ten-40haipc0xl.vercel.app).
- Select **Shakti Precision Tools** and enter as **Credit Analyst**.
- Inspect Evidence Passport and reconciliation, then run the assessment.
- Review the baseline limit, adverse capacity, DSCR and binding constraint.
- Submit the analyst recommendation.
- Continue as **Sanctioning Authority** and decide within mandate.
- Seal the canonical Decision Package.
- Verify the SHA-256 package hash.
- Execute Independent Replay.

Then inspect:

- **Navprerna** — missing evidence produces `INSUFFICIENT_TO_ASSESS`, no positive offer and an evidence-recovery path.
- **Rangrez** — GST-versus-bank inconsistency produces review escalation instead of unsafe approval.
- **Nirmaan** — adverse capacity and policy gates produce a zero binding limit and decline recommendation.

## 4. Claim-to-proof matrix

| Judge question | Product proof | Repository proof |
|---|---|---|
| Does the system abstain when evidence is insufficient? | Navprerna returns no positive offer and requests additional evidence. | [`docs/DECISION_ASSURANCE.md`](docs/DECISION_ASSURANCE.md), release evidence, API tests |
| Does it detect conflicting source data? | Rangrez is routed to review on reconciliation risk. | Evidence and reconciliation services; BOLA and E2E tests |
| Is the proposed amount financially supportable? | Shakti exposes reducing-balance EMI, baseline/adverse capacity, post-loan DSCR and binding limit. | Financial-capacity reference tests and assurance cohort |
| Can a human change the mathematics? | Human users may recommend, condition or decline but cannot overwrite engine outputs. | Role-gating and policy-invariant tests |
| Can an analyst self-sanction? | Credit Analyst cannot issue the final sanction. | RBAC/BOLA tests and governed action matrix |
| Can an authority exceed mandate? | Out-of-mandate sanctions fail closed. | `OUTSIDE_SANCTION_MANDATE` tests |
| Can another role seal the package? | Only `SANCTIONING_AUTHORITY` may seal. | Release-evidence package-verification result |
| Can a package be altered silently? | Canonical payload is sealed with SHA-256 and can be verified. | Decision-assurance and verification tests |
| Can the bank reproduce an old decision? | Independent Replay re-runs the historical scoring and capacity engines over the sealed snapshot. | `INDEPENDENT REPLAY MATCHED` release evidence |
| Is the demo merely a polished frontend? | Live API, Swagger, database-backed workflow and role-specific mutations are independently inspectable. | Backend routes, migrations, tests and exact deployment SHA |

## 5. Decision-system card

### Intended use

AI-assisted assessment of Indian MSME working-capital and term-credit cases using consented alternate evidence, deterministic financial calculations and human-controlled sanctioning.

### System type

- Deterministic evidence-conditioned Financial Health Score and policy engine.
- Deterministic Financial Capacity Engine.
- Deterministic Stress Lab and Bankability Path.
- Human maker-checker sanction workflow.
- Cryptographically sealed decision package with verify and replay.
- Optional LLM commentary is isolated from numerical calculations and cannot alter score, policy, limit or sanction outcome.

### Inputs represented by the prototype

- Account Aggregator-shaped banking evidence.
- GST turnover and filing evidence.
- Existing debt obligations and bureau-style evidence.
- Business profile and product request.
- Policy thresholds, authority mandate and stress parameters.

The public prototype uses deterministic seeded evidence and adapter-ready contracts. It does **not** claim live private access to IDBI, GSTN, AA, bureau, ULI, OCEN or CBS systems.

### Outputs

- Evidence coverage and integrity state.
- Explainable Financial Health Score where evidence is sufficient.
- Baseline and adverse supportable amount.
- EMI, post-loan DSCR, leverage and binding constraint.
- Policy recommendation and Bankability Path.
- Analyst recommendation and authority decision.
- Canonical sealed Decision Package.
- Verification and independent replay result.

### Human oversight

| Role | Authority boundary |
|---|---|
| Relationship Manager | Originates and supplies evidence; cannot assess or sanction. |
| Credit Analyst | Assesses and recommends; cannot sanction. |
| Sanctioning Authority | Decides within monetary mandate; cannot alter engine mathematics. |
| Auditor | Verifies and replays; cannot mutate the case. |
| Risk Administrator | Maintains policy controls; cannot decide individual cases. |

### Validation performed

- 116 backend tests.
- 29 frontend tests.
- Deployed Playwright journey.
- 1,000-case deterministic invariant cohort.
- 25 independent replay checks.
- Security, dependency and static-analysis gates recorded in release evidence.

### Known limitations

- Synthetic deterministic personas, not an IDBI outcome-labelled training cohort.
- No regulator, bank or production certification is claimed.
- External government and financial rails are represented by contracts/adapters, not production credentials.
- Credit policy thresholds require IDBI validation and formal approval before pilot use.
- Any statistical PD or ML challenger would require IDBI-governed development, calibration, OOT validation, fairness analysis and monitoring before influencing production decisions.

## 6. IDBI shadow-pilot runbook

### Pilot objective

Validate whether the governed decision layer reduces evidence rework and credit-processing friction while preserving human authority, financial safety and complete auditability.

### Recommended pilot mode

**Shadow mode only.** Vyapar Pulse produces an assessment package beside the existing IDBI process. It does not auto-approve, disburse or modify the bank's system of record.

### Proposed cohort

- 25–50 MSME working-capital or term-credit cases.
- A deliberate mix of established, thin-file, evidence-incomplete and stressed businesses.
- No customer-facing decision should rely solely on the prototype during the shadow phase.

### Four-week sequence

| Week | Scope | Exit gate |
|---|---|---|
| 0 | Security review, data minimisation, field mapping, policy mapping and deployment boundary | Approved data contract and named control owners |
| 1 | Read-only ingestion adapters and evidence reconciliation | Source fields traceable; missing sources never silently imputed as adverse |
| 2 | Shadow scoring, capacity and stress comparison against officer workflow | Calculation reconciliation and documented exception taxonomy |
| 3 | Maker-checker workflow, mandate enforcement, package sealing and replay | Unauthorized actions fail closed; every completed case verifies and replays |
| 4 | KPI review, exception analysis and go/no-go recommendation | Signed pilot report and decision on recalibration, extension or closure |

### Minimum pilot acceptance gates

1. **Evidence gate:** incomplete mandatory evidence cannot produce a positive automated offer.
2. **Reconciliation gate:** material cross-source conflicts are surfaced and routed to review.
3. **Capacity gate:** adverse supportable amount never exceeds baseline supportable amount.
4. **Policy gate:** hard DSCR or leverage failures bind the eligible amount to zero where configured.
5. **Authority gate:** analyst self-sanction and out-of-mandate authority actions fail closed.
6. **Integrity gate:** every finalized package verifies against its canonical SHA-256 hash.
7. **Replay gate:** every sampled finalized package independently reproduces the recorded mathematical result.
8. **Truth gate:** unavailable integrations, labels and certifications remain explicitly disclosed.

### Suggested pilot KPIs

- Evidence-completeness rate at first review.
- Number of cross-source discrepancies found before sanction.
- Manual rework cycles per case.
- Time from complete evidence to analyst recommendation.
- Difference between requested and financially supportable amount.
- Cases abstained, referred, conditionally offered and declined.
- Mandate exceptions prevented.
- Package verification and replay success rate.
- Officer agreement/disagreement with each recommendation and documented reason.

### Integration boundary

```text
IDBI channels / LPS / i-MSME Express
        |
        v
Bank-controlled adapter layer
  - CBS / existing customer relationship
  - consented AA / GST / bureau / EPFO feeds
        |
        v
Vyapar Pulse governed decision service
  Evidence -> Reconciliation -> FHI -> Capacity -> Stress -> Policy
        |
        v
Analyst -> Sanctioning Authority -> Seal -> Verify -> Replay
        |
        v
Signed decision package returned to IDBI system of record
```

Production integration should use bank-managed identities, secrets, encryption, audit retention, network controls and policy configuration. The public demo credentials and seeded evidence are not pilot credentials.

## 7. Rubric coverage

| Evaluation lens | Existing proof |
|---|---|
| Innovation | Evidence-conditioned abstention plus governed sanction, cryptographic sealing and independent historical replay. |
| Feasibility | Working full-stack application, live API, database-backed workflow, container setup and exact release evidence. |
| Technical depth | Financial-capacity mathematics, stress invariants, role governance, idempotency, BOLA, package verification and replay. |
| Scalability | Adapter boundary for bank and consented rails; model-agnostic scoring layer; stateless decision calculations around persisted workflow state. |
| Business impact | Safer amount determination, reduced evidence rework, controlled exceptions and auditable officer accountability. |
| Governance | Explicit human authority, no LLM control of mathematics, truth boundaries, fail-closed gates and reproducible decisions. |

## 8. Primary evidence index

- [`README.md`](README.md) — judge entry point, live product, screenshots and complete product overview.
- [`docs/RELEASE_EVIDENCE.md`](docs/RELEASE_EVIDENCE.md) — exact SHAs, tests, deployment record and verified outcomes.
- [`docs/DECISION_ASSURANCE.md`](docs/DECISION_ASSURANCE.md) — benchmark assertions and exact decision behavior.
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — institutional security and trust boundaries.
- [`docs/architecture/SYSTEM_ARCHITECTURE.md`](docs/architecture/SYSTEM_ARCHITECTURE.md) — system architecture.
- [`artifacts/validation/release_assurance.json`](artifacts/validation/release_assurance.json) — machine-readable deterministic assurance evidence.
- [Swagger / OpenAPI](https://vyapar-pulse-backend.vercel.app/docs) — live schemas and API inspection.

---

**Winning distinction:** Vyapar Pulse does not merely estimate who is risky. It proves whether evidence was sufficient, calculates how much can be safely supported, controls who may authorize the decision, seals the complete package and independently reproduces why every sanctioned rupee was approved.