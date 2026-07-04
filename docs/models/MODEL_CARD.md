# Model Card: Vyapar Pulse Deterministic Scorer

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
