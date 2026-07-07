#!/bin/bash
set -e

echo "====================================="
echo "Vyapar Pulse - Full Verification Suite"
echo "====================================="

echo "[1/4] Running Backend Tests..."
cd backend
source .venv/bin/activate
pytest -v
cd ..

echo "[2/4] Running Backend Typecheck..."
cd backend
source .venv/bin/activate
mypy app/
cd ..

echo "[3/4] Running Frontend Linter & Typecheck..."
cd frontend
npm run lint
npm run type-check
cd ..

echo "[4/4] Running Decision Assurance E2E..."
make verify

echo "====================================="
echo "✅ ALL VERIFICATIONS PASSED"
echo "====================================="
