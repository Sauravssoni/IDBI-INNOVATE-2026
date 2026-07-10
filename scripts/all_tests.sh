#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export DATABASE_URL="${DATABASE_URL:?DATABASE_URL is required}"
export DEMO_DATABASE_URL="${DEMO_DATABASE_URL:-$DATABASE_URL}"
export DEMO_USER_PASSWORD="${DEMO_USER_PASSWORD:?DEMO_USER_PASSWORD is required}"
export JWT_SECRET="${JWT_SECRET:?JWT_SECRET is required}"

cleanup() {
  echo "Stopping any background services..."
  lsof -ti:3005,8000 | xargs -I {} sh -c 'ps -p {} -o comm= | grep -qE "(node|python|uvicorn)" && kill -9 {}' 2>/dev/null || true
}
trap cleanup EXIT

echo "Checking git status before tests..."
if [ -n "$(git status --porcelain)" ]; then
  echo "Git working directory is not clean before tests."
  exit 1
fi

echo "Seeding Test Database for Backend Tests..."
cd "$REPO_ROOT/backend"
PYTHONPATH=. python -m app.seed.run_demo_reset

echo "Running Backend Tests..."
cd "$REPO_ROOT/backend"
pytest -v --cov=app --cov-report=term-missing --cov-fail-under=85
ruff check app tests scripts
ruff format --check app tests scripts
mypy app
bandit -r app -ll
pip-audit -r requirements.txt

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
PYTHONPATH=. python -m app.seed.run_demo_reset

echo "Running Frontend E2E Tests..."
cd "$REPO_ROOT/frontend"
npx playwright test

echo "Running Proofs..."
cd "$REPO_ROOT/backend"
PYTHONPATH=. python -m app.seed.run_demo_reset

mkdir -p "$REPO_ROOT/artifacts/runtime"
export RUNTIME_EVIDENCE_DIR="$REPO_ROOT/artifacts/runtime"
PYTHONPATH=. python scripts/run_decision_assurance.py > "$RUNTIME_EVIDENCE_DIR/decision_assurance.json"
PYTHONPATH=. python scripts/run_demo_walkthrough.py > "$RUNTIME_EVIDENCE_DIR/demo_walkthrough.json"
python ../scripts/deployment_smoke_test.py

echo "Checking git status after tests..."
cd "$REPO_ROOT"
if [ -n "$(git status --porcelain | grep -v -E 'artifacts/runtime/|docs/assets/screenshots/')" ]; then
  echo "Git working directory is not clean after tests. Some tests mutated the workspace."
  git status --short
  exit 1
fi

echo "All tests passed successfully!"
