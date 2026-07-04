#!/bin/bash
set -e

# Define prohibited terms
# We use grep -i to be case-insensitive
# We check in Python, TypeScript/JavaScript, and Markdown files
PROHIBITED_TERMS=("AUTO_APPROVE" "AUTO_APPROVED" "AUTO_SANCTION" "AI_APPROVED" "FINAL_APPROVAL" "APPROVED_BY_MODEL")

echo "Running CI Prohibited Terms Check..."

has_errors=0

for term in "${PROHIBITED_TERMS[@]}"; do
    echo "Checking for prohibited term: $term"
    # Find files matching the criteria, ignoring .venv, node_modules, .git, and migrations
    matches=$(find backend frontend -type d \( -name ".venv" -o -name "node_modules" -o -name ".git" -o -name "alembic" \) -prune -o -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.md" \) -print0 | xargs -0 grep -in "$term" || true)
    
    if [ -n "$matches" ]; then
        echo "ERROR: Found prohibited term '$term' in the following locations:"
        echo "$matches"
        has_errors=1
    fi
done

if [ $has_errors -eq 1 ]; then
    echo "CI CHECK FAILED: Prohibited terms found. The system must not autonomously approve, reject or sanction credit."
    exit 1
else
    echo "CI CHECK PASSED: No prohibited terms found."
    exit 0
fi
