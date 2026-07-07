#!/bin/bash
echo "=== Running Security & Linting Suite ==="
cd /Users/tzar/Desktop/Idbi/vyapar-pulse-starter/backend
source .venv/bin/activate
echo ">> Running ruff..."
ruff check .
echo ">> Running mypy..."
mypy .
echo ">> Running bandit..."
bandit -r . -ll -ii
echo ">> Running pip-audit..."
pip-audit
echo ">> Running pytest..."
DATABASE_URL="postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test" pytest -v
cd ../frontend
echo ">> Running eslint..."
npm run lint || npx eslint .
echo ">> Running tsc..."
npx tsc --noEmit
echo ">> Running vitest..."
npx vitest run
echo "=== Suite Complete ==="
