#!/usr/bin/env bash
set -euo pipefail

echo "Installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running migrations and seeding demo database..."
PYTHONPATH=. python -m app.seed.run_demo_reset

echo "Build and seed complete."
