#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export DATABASE_URL="${DATABASE_URL:-postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test}"
export DEMO_DATABASE_URL="${DEMO_DATABASE_URL:-$DATABASE_URL}"
export DEMO_USER_PASSWORD="${DEMO_USER_PASSWORD:-testpassword123}"
export JWT_SECRET="${JWT_SECRET:-replace_this_with_a_secure_random_string_for_production}"

cleanup() {
  echo "Stopping any background services on ports 3005 and 8000..."
  lsof -ti:3005,8000 | xargs kill -9 2>/dev/null || true
}
trap cleanup EXIT
cleanup || true

echo "Checking git status before tests..."
if [ -n "$(git status --porcelain)" ]; then
  echo "Git working directory is not clean before tests."
  exit 1
fi

echo "Seeding Test Database for Backend Tests..."
cd "$REPO_ROOT/backend"
PYTHONPATH=. uv run python -m app.seed.run_demo_reset

echo "Running Backend Tests..."
cd "$REPO_ROOT/backend"
uv run pytest -v --cov=app --cov-report=term-missing --cov-fail-under=85
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run mypy app
uv run bandit -r app -ll
uv run pip-audit -r requirements.txt

echo "Running Frontend Tests..."
cd "$REPO_ROOT/frontend"
npm ci
npm audit --audit-level=high
npm run lint
npm run type-check
npm test -- --reporter=verbose
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run build

echo "Installing Playwright Browser..."
npx playwright install chromium --with-deps

echo "Seeding Test Database for E2E..."
cd "$REPO_ROOT/backend"
PYTHONPATH=. uv run python -m app.seed.run_demo_reset

echo "Running Frontend E2E Tests..."
cleanup || true
cd "$REPO_ROOT/frontend"
npx playwright test
cleanup || true

echo "Running Proofs..."
cd "$REPO_ROOT/backend"
PYTHONPATH=. uv run python -m app.seed.run_demo_reset

mkdir -p "$REPO_ROOT/artifacts/runtime"
export RUNTIME_EVIDENCE_DIR="$REPO_ROOT/artifacts/runtime"
PYTHONPATH=. uv run python scripts/run_decision_assurance.py > "$RUNTIME_EVIDENCE_DIR/decision_assurance.json"
PYTHONPATH=. uv run python scripts/run_demo_walkthrough.py > "$RUNTIME_EVIDENCE_DIR/demo_walkthrough.json"
cleanup || true
echo "Starting background servers for smoke test..."
cd "$REPO_ROOT/backend"
APP_ENV="development" DATABASE_URL="$DATABASE_URL" JWT_SECRET="$JWT_SECRET" DEMO_USER_PASSWORD="$DEMO_USER_PASSWORD" DEMO_ACCESS_ENABLED="true" PYTHONPATH=. uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
cd "$REPO_ROOT/frontend"
npm run start -- -p 3005 > /dev/null 2>&1 &

echo "Waiting for servers to start..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1 && curl -s http://127.0.0.1:3005 >/dev/null 2>&1; then
    echo "Servers started successfully."
    break
  fi
  sleep 1
done

cd "$REPO_ROOT/backend"
uv run python ../scripts/deployment_smoke_test.py

echo "Checking git status after tests..."
cd "$REPO_ROOT"
if [ -n "$(git status --porcelain | grep -v -E 'artifacts/runtime/|artifacts/decision_assurance.json|artifacts/demo_walkthrough.json|docs/DECISION_ASSURANCE.md|docs/assets/screenshots/')" ]; then
  echo "Git working directory is not clean after tests. Some tests mutated the workspace."
  git status --short
  exit 1
fi

echo "All tests passed successfully!"
