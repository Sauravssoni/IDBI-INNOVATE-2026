# Decision Assurance

The Vyapar Pulse Starter includes a mechanism to verify that our credit evaluation logic consistently arrives at the intended outcomes across all four core personas. 

This ensures that any modifications to the system (database schemas, evaluation logic, or migration scripts) do not inadvertently break the required business rules.

## The Personas

1. **Shakti Precision**
   - **Condition:** Strong business, high DSCR (1.85).
   - **Expected Outcome:** Conditional Offer (~₹35.7 lakh supportable structure).

2. **Navprerna Tech Solutions**
   - **Condition:** Missing required evidence or lack of confidence.
   - **Expected Outcome:** Additional Evidence Required.

3. **Rangrez Textiles**
   - **Condition:** Seasonal cash-flow patterns with adequate annual capacity.
   - **Expected Outcome:** Conditional Offer (Analyst recommends alternative structure).

4. **Aarohan Infrastructure**
   - **Condition:** High existing debt obligations leading to low DSCR (1.05).
   - **Expected Outcome:** Decline.

## Verification

To run the verification suite:

```bash
cd backend
python -m app.seed.seed_all_demo
PYTHONPATH=. python scripts/run_decision_assurance.py
```

If the underlying logic is tampered with, `run_decision_assurance.py` will fail with a non-zero exit code due to assertion errors. This creates a reproducible, automated proof of correctness for the Vyapar Pulse architecture.
