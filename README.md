# VYAPAR PULSE AI

An Evidence-First Financial Health Card, MSME Credit Twin, and Safe-Offer Engine for credit-invisible Indian MSMEs. Built for the **IDBI Innovate 2026 Track 03** submission by **Syntheon Technology Private Limited**.

## Mission
Vyapar Pulse AI helps banking institutions assess New-to-Bank (NTB) MSMEs lacking traditional financial documents. It achieves this by combining synthetic GST data, consented Account Aggregator-style banking data, UPI aggregates, EPFO employment trends, and invoice metrics into a deterministic, fully explainable "Credit Twin". 

This is **not** a generic dashboard and **not** an LLM wrapper. LLMs are strictly bounded to generating narrative summaries; the authoritative scoring logic is 100% deterministic, monotonic, and bounded code.

## Key Capabilities & Safety Invariants
- **Deterministic Bounded Scoring:** Scores (Health, Evidence, Resilience) are mathematically guaranteed to remain between `[0, 100]`.
- **Monotonic Stress Response:** As risk factors (e.g., buyer concentration, payment delays) increase, resilience scores strictly decrease or remain stable.
- **Evidence-Linking:** Every feature is derived directly from auditable underlying data (GST, Bank, EPFO).
- **Strict Architecture Boundaries:** LLMs cannot modify authoritative scores. Data flows via a strict Clean Architecture pattern.

## Architecture

```mermaid
graph TD
    A[Frontend: Next.js] -->|REST API| B[Backend: FastAPI]
    B --> C[Feature Engine]
    C --> D[Scoring Engine]
    D --> E[Decision Policy]
    B --> F[(PostgreSQL)]
    F --> |Synthetic Evidence| C
```

## Documentation
Please refer to the `docs/` directory for mandatory banking and security documentation:
- `docs/security/SECURITY_ARCHITECTURE.md`
- `docs/security/THREAT_MODEL.md`
- `docs/security/PRIVACY_AND_CONSENT.md`
- `docs/security/INCIDENT_RESPONSE.md`
- `docs/security/SECURITY_TEST_REPORT.md`
- `docs/models/MODEL_CARD.md`
- `docs/models/DATA_CARD.md`
- `docs/models/SCORING_METHODOLOGY.md`
- `docs/privacy/RESPONSIBLE_AI.md`

## Differentiators

Unlike standard dashboards or LLM-wrappers, Vyapar Pulse is an **Evidence-First** engine:
1. **Deterministic Bounded Scoring:** Financial Health, Evidence, and Resilience scores are mathematically bounded `[0, 100]`.
2. **Monotonic Stress Response:** As risk factors (e.g., buyer concentration, payment delays) increase, resilience scores strictly decrease or remain stable.
3. **No LLM Hallucinations in Core Logic:** Authoritative credit decisions, policy constraints, and offer generation are 100% deterministic code. LLMs are strictly bounded to generating explainable narrative summaries of the numeric data.
4. **Idempotent Audit Trails:** Every system action and human decision is immutably logged with cryptographic hashing, ensuring complete BOLA (Broken Object Level Authorization) protection.

## Demo Personas

The prototype includes four distinct MSME archetypes to demonstrate the decision engine's edge cases:

| Legal Name | Persona Profile | Key Constraint | System Recommendation |
| :--- | :--- | :--- | :--- |
| **Shakti Precision Components** | Ideal "Credit-Invisible" MSME. 18 months of GST & AA data. | None | **CONDITIONAL_OFFER** / **READY_FOR_REVIEW** |
| **Navprerna Tech Solutions** | Genuinely missing periods or source evidence. | Low Evidence Confidence | **ADDITIONAL_EVIDENCE_REQUIRED** |
| **Rangrez Textiles** | Viable but highly seasonal cash flows. | High Revenue CV | **READY_FOR_REVIEW** (or CONDITIONAL_OFFER) |
| **Aarohan Infrastructure** | High existing debt obligations. | Low DSCR (< 1.15) | **DECLINE_RECOMMENDED** |

## Quick Start & Credentials

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

### Setup Instructions

1. **Start the Database**
```bash
docker-compose up -d db
```

2. **Initialize Backend & Run Migrations**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

3. **Generate Synthetic Data (All 4 Personas)**
```bash
DEMO_USER_PASSWORD=demopassword ALLOW_DANGEROUS_CORS=true PYTHONPATH=. python -m app.seed.seed_all_demo
```

4. **Run the Backend API**
```bash
DEMO_USER_PASSWORD=demopassword ALLOW_DANGEROUS_CORS=true uvicorn app.main:app --host 0.0.0.0 --port 8001
```

5. **Run the Frontend (In a new terminal)**
```bash
cd frontend
npm install
npm run dev
```

### Demo Credentials

| Role | Email | Password | Allowed Actions |
| :--- | :--- | :--- | :--- |
| **Relationship Manager (RM)** | `rm@vyaparpulse.com` | `demopassword` | View cases, View read-only assessment, Acknowledge decisions |
| **Credit Analyst (CA)** | `ca@vyaparpulse.com` | `demopassword` | Run assessment, View full details, Submit recommendation |
| **Sanctioning Authority (SA)** | `sa@vyaparpulse.com` | `demopassword` | Review CA recommendations, Approve/Decline |

## Known Limitations & Future Work
- **Sandbox Rules:** The credit policies and limits in `SafeLimitEngine` (e.g. 20% Nayak Committee heuristic) are illustrative prototype assumptions, not exact IDBI production policies.
- **LLM Connectivity:** The generative explanation feature requires an active OpenAI API key or Azure OpenAI configuration to operate.
- **Mock Aggregator:** The Account Aggregator implementation uses synthetic seeded data rather than a live Sahamati sandbox connection.

## Repository Quality Standards
This repository enforces:
- Clean Architecture (API, Core, Domain, DB layers isolated)
- SQLAlchemy ORM with Alembic schema migrations
- Deterministic data seeding for reproducibility
- Security by design (threat models, access controls, BOLA checks)
