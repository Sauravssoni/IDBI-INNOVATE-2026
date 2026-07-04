# Responsible AI Principles

1. **Human in the Loop:** The "Safe-Offer Engine" recommends decisions (READY_FOR_REVIEW, CONDITIONAL_OFFER, DECLINE_RECOMMENDED). Final sanctioning authority remains with human officers.
2. **Explainability First:** The use of deterministic scoring ensures that if an MSME asks "Why was I declined?", the bank can provide an exact, mathematical reason (e.g., "Buyer concentration exceeded 60%").
3. **Safe Fallbacks:** If data is missing or stale, the Evidence Confidence score drops, automatically shifting the recommendation to ADDITIONAL_EVIDENCE_REQUIRED or DECLINE_RECOMMENDED.
4. **Fairness:** The algorithm relies purely on cash-flow metrics. It does not ingest demographic data (age, gender, caste, religion) of the business owners.
