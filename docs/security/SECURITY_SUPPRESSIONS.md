# Security Suppressions Audit

This document records all intentional security scanner suppressions (e.g., `# nosec`) in the Vyapar Pulse codebase. 
Any suppression must include the rule ID, justification, scope, and review conditions.

## 1. Bandit Suppressions (Python)

| File | Line | Rule ID | Reason | Scope | Safety Justification | Compensating Control | Reviewer | Expiry / Condition |
|------|------|---------|--------|-------|----------------------|----------------------|----------|--------------------|
| `backend/app/seed/seed_shakti.py` | 18 | B105 | Hardcoded password | Test Seed | Only populates local/development database with default mock user accounts. Never executed in production paths. | Secrets module used for actual authentication hashes. | Antigravity AI | Remove if seed strategy moves to ENV vars. |
| `backend/app/seed/seed_shakti.py` | 19 | B105 | Hardcoded password | Test Seed | Same as above. | Same as above. | Antigravity AI | Same as above. |
| `backend/app/seed/seed_shakti.py` | 20 | B105 | Hardcoded password | Test Seed | Same as above. | Same as above. | Antigravity AI | Same as above. |
| `backend/app/seed/seed_shakti.py` | 99 | B311 | `random` use | Test Seed | Generates deterministic mock business revenue fluctuations for UI demonstration. | Not used for cryptography, tokens, or sessions. | Antigravity AI | Permanent for mock generation. |
| `backend/app/seed/seed_shakti.py` | 113 | B311 | `random` use | Test Seed | Generates deterministic mock bank transaction amounts. | Not used for cryptography, tokens, or sessions. | Antigravity AI | Permanent for mock generation. |
| `backend/app/seed/seed_shakti.py` | 150 | B311 | `random` use | Test Seed | Generates deterministic employee counts for EPFO mock data. | Not used for cryptography, tokens, or sessions. | Antigravity AI | Permanent for mock generation. |
| `backend/app/seed/seed_shakti.py` | 162 | B311 | `random` use | Test Seed | Generates deterministic invoice amounts. | Not used for cryptography, tokens, or sessions. | Antigravity AI | Permanent for mock generation. |
| `backend/app/seed/seed_shakti.py` | 170 | B311 | `random` use | Test Seed | Generates deterministic invoice dates. | Not used for cryptography, tokens, or sessions. | Antigravity AI | Permanent for mock generation. |
| `backend/app/seed/seed_shakti.py` | 201 | B311 | `random` use | Test Seed | Generates deterministic invoice settlement dates. | Not used for cryptography, tokens, or sessions. | Antigravity AI | Permanent for mock generation. |

## CI Enforcement

A CI step inside the quality gate explicitly verifies that no `# nosec` is used without an attached rule ID. `grep -rnw "app/" -e "# nosec$"` is used to enforce this policy.
