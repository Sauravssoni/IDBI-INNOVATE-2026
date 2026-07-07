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
pytest -v
cd ../frontend
echo ">> Running eslint..."
npm run lint || npx eslint .
echo ">> Running tsc..."
npx tsc --noEmit
echo ">> Running vitest..."
npx vitest run
echo "=== Suite Complete ==="
