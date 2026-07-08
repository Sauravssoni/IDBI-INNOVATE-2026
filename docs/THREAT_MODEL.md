# Threat Model

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
