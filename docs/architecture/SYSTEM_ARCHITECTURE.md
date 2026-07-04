# Architecture

## Logical flow

Consent & identity → Source adapters → Normalization → Evidence graph → Feature store → Scoring ensemble → Policy gateway → Stress/structure optimizer → Explanations → Officer decision → Monitoring

## Services

### 1. Consent and purpose service
Records data source, purpose, expiry, revocation and access history. No downstream service reads customer data without an active purpose grant.

### 2. Source adapters
Interfaces for Account Aggregator/FIP payloads, GST summaries, bank transactions, UPI/merchant aggregates, bureau data, invoices and optional business-operational signals.

### 3. Evidence reconciliation
Resolves entity identity and tests whether bank inflows, GST turnover, invoices and declared obligations agree within explainable tolerances.

### 4. Feature store
Versioned, time-stamped derived features. Every feature retains lineage to source evidence.

### 5. Scoring ensemble
- Interpretable tabular model for health/risk
- Time-series model for cash-flow forecast
- Graph analytics for concentration and circularity
- Anomaly model for inconsistent or manipulated patterns
- Deterministic policy rules for hard constraints

### 6. Confidence and abstention layer
Produces an independent confidence score using completeness, freshness, identity match, cross-source agreement and anomaly risk.

### 7. Structure optimizer
Tests product, amount, tenure and repayment structures against cash-flow and stress constraints.

### 8. Explanation service
Generates evidence-linked drivers. LLM output, if used, is grounded only in approved structured results and cannot alter scores or policy outcomes.

### 9. Governance plane
Model registry, champion/challenger testing, drift monitoring, bias analysis, access control, consent audit and human override reasons.

## Production controls

- PII vault separated from analytical identifiers
- Encryption in transit and at rest
- Field-level tokenization for sensitive identifiers
- Role and purpose-based access
- Tamper-evident append-only audit events
- Data minimization and configurable retention
- No customer data in model prompts by default
- Human approval for consequential decisions
- Shadow-mode validation before policy use
