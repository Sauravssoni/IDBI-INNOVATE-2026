#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Running Backend Tests..."
cd "$REPO_ROOT/backend"
export DATABASE_URL="postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test"
export JWT_SECRET="test-secret"
export DEMO_USER_PASSWORD="${DEMO_USER_PASSWORD:?required}"
pytest -v --cov=app --cov-report=term-missing --cov-fail-under=85
ruff check app tests scripts
ruff format --check app tests scripts
mypy app
bandit -r app -ll
pip-audit -r requirements.txt

echo "Running Frontend Tests..."
cd "$REPO_ROOT/frontend"
npm ci
npm audit --audit-level=high || true
npm run lint
npm run type-check
npm test -- --reporter=verbose
npm run build

echo "Running Proofs..."
cd "$REPO_ROOT/backend"
unset DATABASE_URL
if [ -f "$REPO_ROOT/.env" ]; then
  export $(grep -v '^#' "$REPO_ROOT/.env" | xargs)
fi
export DEMO_USER_PASSWORD="${DEMO_USER_PASSWORD:?required}"
PYTHONPATH=. python -m app.seed.run_demo_reset
PYTHONPATH=. python scripts/run_decision_assurance.py
PYTHONPATH=. python scripts/run_demo_walkthrough.py
python ../scripts/deployment_smoke_test.py
