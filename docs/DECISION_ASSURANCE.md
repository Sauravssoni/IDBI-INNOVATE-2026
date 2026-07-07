# Decision Assurance

The Vyapar Pulse Starter includes a stringent, deterministic mechanism to verify that our credit evaluation logic consistently arrives at the intended outcomes and abides by all security, safety, and business rules across the four core personas. 

This ensures that any modifications to the system (database schemas, evaluation logic, or migration scripts) do not inadvertently break the required business rules or security models. The assurance script acts as an executable proof of correctness.

## Required Assertions

The `run_decision_assurance.py` script rigorously checks the following guarantees every time it runs. **Every mismatch causes an immediate failure.**

### 1. The Core Personas
1. **Exactly four unique personas** are seeded and verified.
2. **Shakti Precision**
   - Condition: Strong business.
   - Outcome: DSCR is exactly `1.85`.
   - Recommendation: `CONDITIONAL_OFFER`.
   - Binding Limit: Supportable amount is approximately ₹35.7 lakh (`3500000 <= limit <= 3600000`).
3. **Navprerna Tech Solutions**
   - Condition: Missing required evidence or lack of confidence.
   - Recommendation: `ADDITIONAL_EVIDENCE_REQUIRED`.
4. **Rangrez Textiles**
   - Condition: Seasonal cash-flow patterns.
   - Recommendation: Exact frozen recommendation verified (`READY_FOR_REVIEW` or `CONDITIONAL_OFFER`).
5. **Aarohan Infrastructure**
   - Condition: High existing debt obligations leading to low DSCR (1.05).
   - Recommendation: `DECLINE_RECOMMENDED`.

### 2. Monotonicity & Mathematical Consistency
- **Cash-flow/limit monotonicity**: Increasing revenue (cash-inflow) must strictly yield a higher or equal binding limit.
- **Obligation/DSCR monotonicity**: Increasing existing obligations must strictly yield a lower or equal DSCR.
- **Evidence-confidence monotonicity**: A drop in evidence confidence score (e.g., to 30.0) forces the decision outcome to `ADDITIONAL_EVIDENCE_REQUIRED`, regardless of financials.

### 3. System Guarantees
- **Deterministic Replay**: Calling evaluate multiple times with the same idempotency key must return the exact same cached payload and status.
- **Check-and-Set (CAS) Protection**: Attempting a state transition with a stale version number must return a `409 Conflict`.
- **LLM Isolation**: Scoring and policy evaluation is deterministic. The LLM is explicitly mocked and asserted to **never** be called during core policy execution.
- **Continuous Audit Hash Chain**: Every state transition maintains a cryptographic hash chain. The assurance script verifies that `prior_event_hash` perfectly matches the preceding event's `event_hash` for the entire case history.

### 4. RBAC Guarantees
- **RM cannot evaluate**: Relationship Managers are blocked from triggering automated evaluation.
- **Analyst cannot sanction**: Credit Analysts are blocked from making human sanction decisions.
- **SA Mandate Enforced**: System Administrators or appropriately scoped Sanctioning Authorities are required to sanction.

## Verification

To run the verification suite locally:

```bash
cd backend
python -m app.seed.run_demo_reset
PYTHONPATH=. python scripts/run_decision_assurance.py
```

If the underlying logic is tampered with, `run_decision_assurance.py` will fail with a non-zero exit code. This creates a reproducible, automated proof of correctness for the Vyapar Pulse architecture.
