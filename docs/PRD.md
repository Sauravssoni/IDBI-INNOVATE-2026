# Product Requirements Document — VYAPAR PULSE AI

## Product thesis

A bank should not ask only, “Is this MSME risky?” It should also ask:

- Is the available evidence trustworthy enough to decide?
- What credit structure can this cash flow safely sustain?
- What breaks under stress?
- What is the smallest intervention that can convert the applicant into a safe borrower?

VYAPAR PULSE therefore delivers **Decision + Structure + Intervention**, not merely a score.

## Primary user

IDBI MSME credit officer evaluating a New-to-Bank enterprise with limited bureau history and fragmented digital evidence.

## Secondary users

- Branch relationship manager
- Credit risk and policy team
- Model risk / audit team
- MSME applicant
- Portfolio monitoring team

## Product outputs

1. Financial Health Score — operating and repayment capacity
2. Data Confidence Score — whether evidence is adequate and internally consistent
3. Resilience Score — capacity to survive plausible shocks
4. Evidence Graph — traceable relationship between entity, accounts, tax records, buyers, suppliers, invoices and obligations
5. Safe Structure — product, amount, tenure and conditions
6. Counterfactual Stress Lab — effect of revenue shocks, buyer delays, amount and tenure changes
7. Bankability Plan — prioritized remedial actions
8. Audit Lineage — consent, source, feature, model and human decision history

## Novel wedge

### Confidence-aware abstention

The engine must refuse to automate a recommendation when evidence confidence is inadequate. “Unknown” must not be silently converted into “bad.”

### Credit structure optimization

The system suggests the safest offer the business can sustain instead of deciding only yes/no on the requested amount.

### Recoverable rejection

A declined or incomplete application becomes a measurable 30–90 day improvement pathway, creating a future acquisition funnel.

### Hidden-champion discovery

Strong GST, bank and operating evidence can surface viable MSMEs without traditional bureau depth.

## MVP acceptance criteria

- Ingest three synthetic MSME profiles
- Produce three separate scores and top evidence-linked drivers
- Abstain on low-confidence data
- Demonstrate one hidden-champion case without bureau history
- Run at least two stress scenarios
- Recommend a safer product/amount/tenure
- Generate a bankability plan
- Persist model version and assessment ID
- Complete a full demo in under five minutes

## Non-goals for hackathon MVP

- Live sanctioning
- Production use of real customer PII
- Autonomous credit decisions
- Unvalidated claims of default-prediction accuracy
- Blockchain where a conventional signed audit log is sufficient
