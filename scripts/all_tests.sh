#!/usr/bin/env bash
set -euo pipefail

echo "==============================="
echo "Running BACKEND verification..."
echo "==============================="
cd backend
pip install -q -r requirements.txt
export DATABASE_URL="postgresql://vyapar_local:change-this-local-development-password@localhost:5433/vyapar_pulse_test"
python -m pytest -v --cov=app --cov-report=term-missing --cov-fail-under=85
python -m ruff check app tests scripts
python -m ruff format --check app tests scripts
python -m mypy app
python -m bandit -r app -ll
python -m pip_audit -r requirements.txt
cd ..

echo "==============================="
echo "Running FRONTEND verification..."
echo "==============================="
cd frontend
npm ci
npm audit --audit-level=high
npm run lint
npm run type-check
npm test -- --reporter=verbose
npm run build
cd ..

echo "==============================="
echo "Running PROOF (End-to-End)..."
echo "==============================="
cd backend
if [ -f ../.env ]; then
  export $(grep -v '^#' ../.env | xargs)
fi
python -m app.seed.run_demo_reset
python scripts/run_decision_assurance.py
python scripts/run_demo_walkthrough.py
cd ..

echo "==============================="
echo "✅ All canonical verifications passed!"
echo "==============================="
