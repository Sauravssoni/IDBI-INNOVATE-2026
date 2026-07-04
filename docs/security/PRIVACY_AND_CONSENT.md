# Privacy and Consent Framework

## Principles
Vyapar Pulse AI operates on explicit, informed consent for all data ingestion, mimicking Account Aggregator (AA) flows.

## Consent Lifecycle
1. **PENDING:** RM requests consent from MSME.
2. **ACTIVE:** MSME grants access via AA for a specific duration (e.g., 90 days) and purpose (Credit Assessment).
3. **EXPIRED/REVOKED:** Data connections automatically enter a `STALE` state. Fresh evaluation requires renewed consent.

## Data Minimization
- We do not store raw transaction item names if they contain PII, only categories and amounts necessary for derived features.
- Derived features (e.g., `avg_monthly_revenue`) are persisted, minimizing the need to repeatedly scan raw data.
