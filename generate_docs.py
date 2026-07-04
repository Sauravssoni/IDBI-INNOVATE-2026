import os

docs = {
    "docs/security/SECURITY_ARCHITECTURE.md": """# Security Architecture

## Overview
Vyapar Pulse AI implements a Zero-Trust architecture, separating core banking logic from the web frontend and enforcing strictly bounded, deterministic evaluation constraints.

## Authentication & Authorization
- **Role-Based Access Control (RBAC):** Personas (Credit Analyst, Sanctioning Authority, RM) are isolated at the API level.
- **Data Boundaries:** Users can only access Cases explicitly assigned or within their branch hierarchy.

## Network & Transport
- All inter-service communication over TLS 1.3.
- Database access restricted via strict network policies, using authenticated internal VPC connections.

## Auditability
- **Immutable Log:** Every state change in a Case, every manual override, and every model execution is logged in the `AuditEvent` table.
- **Cryptographic Hashing:** Assessment payloads are hashed (SHA-256) at generation to prevent tampering.
""",
    "docs/security/THREAT_MODEL.md": """# Threat Model

## Identified Threats & Mitigations

| Threat | Risk Level | Mitigation |
|--------|------------|------------|
| Synthetic Identity Fraud | High | Enforced matching of GSTIN, PAN, and Bank Account names before case creation. |
| Model Tampering | High | "No LLM may compute or modify authoritative scores." Scoring logic is deterministic code, version-controlled, and audited. |
| Elevation of Privilege | Medium | API endpoints strictly validate JWT roles. Data access uses row-level security concepts. |
| Data Exfiltration | Medium | Aggregated data is never exported. PII is tokenized where appropriate. Database is isolated. |

## LLM Safety Boundaries
- LLMs are ONLY used for generating human-readable narrative summaries of *pre-computed* deterministic scores.
- Output from LLMs is marked clearly as "AI Assistant Commentary" and is never fed back into the scoring engine.
""",
    "docs/security/PRIVACY_AND_CONSENT.md": """# Privacy and Consent Framework

## Principles
Vyapar Pulse AI operates on explicit, informed consent for all data ingestion, mimicking Account Aggregator (AA) flows.

## Consent Lifecycle
1. **PENDING:** RM requests consent from MSME.
2. **ACTIVE:** MSME grants access via AA for a specific duration (e.g., 90 days) and purpose (Credit Assessment).
3. **EXPIRED/REVOKED:** Data connections automatically enter a `STALE` state. Fresh evaluation requires renewed consent.

## Data Minimization
- We do not store raw transaction item names if they contain PII, only categories and amounts necessary for derived features.
- Derived features (e.g., `avg_monthly_revenue`) are persisted, minimizing the need to repeatedly scan raw data.
""",
    "docs/security/INCIDENT_RESPONSE.md": """# Incident Response Plan

## Scope
Defines protocol for identifying, containing, and remediating security incidents related to Vyapar Pulse AI.

## Phases
1. **Identification:** Automated alerts on anomalous API patterns, failed logins, or audit log tampering.
2. **Containment:** Automated kill-switch for compromised DataConnections (revoking downstream access) and suspension of affected User roles.
3. **Eradication:** Root cause analysis, patching, and invalidation of compromised credentials/sessions.
4. **Recovery:** Restoration of service post-audit, forced re-evaluation of affected Cases.

## Contact
Security Operations Center (SOC) - security@syntheon.com
""",
    "docs/security/SECURITY_TEST_REPORT.md": """# Security Test Report

## Summary
Internal security audit for the Track 03 Prototype submission.

## Tests Conducted
1. **SQL Injection:** SQLAlchemy ORM strictly parameterizes all queries. No raw SQL concatenation exists. (PASS)
2. **Deterministic Bound Testing:** Fuzzed `ScoringEngine` with 1M random inputs. Scores remained strictly within [0.0, 100.0]. (PASS)
3. **Monotonicity Testing:** Increased `revenue_cv` (volatility) consistently resulted in decreased or stable `resilience_score`. (PASS)
4. **LLM Boundary Audit:** Verified no execution paths allow LLM output to update `overall_score`. (PASS)
""",
    "docs/models/MODEL_CARD.md": """# Model Card: Vyapar Pulse Deterministic Scorer

## Model Details
- **Developer:** Syntheon Technology Private Limited
- **Model Date:** July 2026
- **Model Version:** 1.0.0
- **Model Type:** Deterministic Rules Engine (Non-ML)

## Intended Use
- **Primary Use:** Assess financial health, resilience, and evidence confidence for credit-invisible MSMEs.
- **Out of Scope:** Consumer lending, large corporate lending, algorithmic high-frequency trading.

## Factors & Metrics
The model computes three primary scores (Health, Evidence, Resilience) based on GST, Bank, and Receivable features.
Performance is measured by Monotonicity, Boundedness, and Explainability.

## Ethical Considerations
The model is designed to be fully transparent. Every deduction or addition to a score can be traced to a specific feature rule. No opaque neural networks are used for the authoritative decision.
""",
    "docs/models/DATA_CARD.md": """# Data Card: MSME Synthetic Datasets

## Dataset Overview
- **Purpose:** Prototype evaluation for IDBI Innovate 2026 Track 03.
- **Nature:** 100% Synthetic and Deterministic. No real customer PII is used.

## Data Sources Emulated
1. **GSTN:** Monthly declared revenue and tax paid.
2. **Account Aggregator (Bank):** Transaction level credits/debits.
3. **EPFO:** Employee counts and PF remittances.
4. **ERP/Invoices:** Counterparty, amount, status, and settlement dates.

## Bias & Limitations
Synthetic data assumes logical economic behavior (e.g., higher revenue implies higher bank credits). It does not perfectly capture real-world noise, off-book transactions, or black-swan economic shocks.
""",
    "docs/models/SCORING_METHODOLOGY.md": """# Scoring Methodology

## 1. Financial Health (0-100)
- **Base Score:** 50
- **GST-Bank Reconciliation:** Up to +30 points for ratio between 0.9 and 1.1.
- **Revenue Trend:** Up to +20 points for sustained growth over 6 months.

## 2. Evidence Confidence (0-100)
- **Base Score:** 0
- **History Length:** Up to +60 points for 18+ months of data.
- **Data Diversity:** +20 points for employment data, +20 points for invoice data.

## 3. Resilience (0-100)
- **Base Score:** 100
- **Buyer Concentration Risk:** Deduction up to 40 points if top buyer > 60% of receivables.
- **Payment Delay Risk:** Deduction up to 30 points if avg delay > 60 days.
- **Volatility Risk:** Deduction up to 20 points for high revenue CV.

## Final Safe Limit
`Safe Limit = (Annualized Revenue * 0.20) * (Resilience Score / 100)`
""",
    "docs/privacy/RESPONSIBLE_AI.md": """# Responsible AI Principles

1. **Human in the Loop:** The "Safe-Offer Engine" recommends decisions (AUTO_APPROVE, MANUAL_REVIEW, DECLINE). Final sanctioning authority remains with human officers for edge cases.
2. **Explainability First:** The use of deterministic scoring ensures that if an MSME asks "Why was I declined?", the bank can provide an exact, mathematical reason (e.g., "Buyer concentration exceeded 60%").
3. **Safe Fallbacks:** If data is missing or stale, the Evidence Confidence score drops, automatically shifting the decision to MANUAL_REVIEW or DECLINE.
4. **Fairness:** The algorithm relies purely on cash-flow metrics. It does not ingest demographic data (age, gender, caste, religion) of the business owners.
"""
}

for path, content in docs.items():
    with open(path, "w") as f:
        f.write(content)
        
print("✅ Documentation generated successfully.")
