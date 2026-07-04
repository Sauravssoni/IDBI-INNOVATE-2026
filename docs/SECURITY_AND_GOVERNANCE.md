# Security, Compliance and Model Governance

## Decision boundary

The platform is decision support. Credit policy and authorized bank personnel remain the final decision-makers.

## Responsible AI controls

- Separate score and confidence
- Explicit abstention threshold
- Missing bureau history is neutral, not automatically adverse
- Reason codes and evidence lineage
- Human override with mandatory rationale
- Segment-level performance and fairness monitoring
- Model cards and versioned validation reports
- Champion/challenger deployment
- Drift alerts and rollback

## Data controls

- Explicit consent and stated purpose
- Minimum necessary data
- PII tokenization
- Segregated secrets and encryption keys
- Configurable retention and deletion
- Access and export logging
- Synthetic data only in public demo

## Security test plan

- Broken-access-control tests
- Consent-expiry and revocation tests
- Prompt-injection tests for explanation layer
- Data-poisoning and malformed-payload tests
- Feature lineage integrity tests
- Model endpoint rate limiting
- Audit event tamper checks
