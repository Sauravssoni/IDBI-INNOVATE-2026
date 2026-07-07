#!/bin/bash
set -euo pipefail

# Export test database URL for pytest
export DATABASE_URL="postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test"
export PYTHONPATH=.:${PYTHONPATH:-}

# Make sure the test DB exists
docker-compose exec -T db psql -U vyapar_local -d postgres -c "CREATE DATABASE vyapar_pulse_test;" 2>/dev/null || true

cd backend
# Assume virtualenv is loaded if running locally, otherwise rely on system python
source .venv/bin/activate || true

pytest -v --cov=app --cov-report=term-missing --cov-fail-under=85
ruff check app tests scripts
ruff format --check app tests scripts
mypy app
bandit -r app -ll
pip-audit -r requirements.txt
cd ..

cd frontend
npm ci
npm audit --audit-level=high
npm run lint
npm run type-check
npm test -- --reporter=verbose
npm run build
cd ..

# Ensure the demo DB is reset for assurance tests
export DATABASE_URL="postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse"
cd backend
source .venv/bin/activate || true
DEMO_USER_PASSWORD="demopassword" python -m app.seed.run_demo_reset
cd ..

# Wait for backend to be ready if needed, or we can just run the scripts which use TestClient
# Note: Since they use TestClient, they access the DB directly without needing the server to be running.
export DEMO_USER_PASSWORD="demopassword"

echo "Running decision assurance..."
python backend/scripts/run_decision_assurance.py

echo "Running demo walkthrough..."
python backend/scripts/run_demo_walkthrough.py

echo "====================================="
echo "✅ ALL VERIFICATIONS PASSED"
echo "====================================="
