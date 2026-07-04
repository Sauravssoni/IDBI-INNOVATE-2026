# VYAPAR PULSE AI

**Credit Readiness & Resilience OS for New-to-Bank MSMEs**

A bank-grade starter repository for the IDBI Innovate 2026 Financial Health Score track.

VYAPAR PULSE does not produce a black-box score alone. It produces an evidence-backed decision package:

1. Financial Health Score
2. Data Confidence Score
3. Safe credit structure and product fit
4. Stress-test results
5. Explainable positive and negative drivers
6. Bankability action plan
7. Consent and audit lineage

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API and `prototype/index.html` for the zero-dependency demo UI.

## Test

```bash
cd backend
pytest -q
```

## Core endpoints

- `GET /health`
- `GET /api/v1/demo-cases`
- `POST /api/v1/assess`
- `POST /api/v1/simulate`
- `POST /api/v1/consents`
- `POST /api/v1/human-decisions`
- `GET /api/v1/audit/{assessment_id}`

## Design principle

LLMs never decide credit. Deterministic policy rules and interpretable statistical/ML models produce risk outputs; language models may only summarize evidence for authorized users.
