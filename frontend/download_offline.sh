#!/bin/bash
if [ -z "$SESSION_TOKEN" ]; then
  echo "Error: SESSION_TOKEN environment variable is required."
  exit 1
fi

CASES=$(cat public/snapshots/cases_list.json | jq -r '.[].id')
for id in $CASES; do
  echo "Downloading for $id"
  # 1. Package
  curl -s http://127.0.0.1:8000/api/cases/$id/decision-package -H "Cookie: vyapar_session_token=$SESSION_TOKEN" | jq . > public/snapshots/${id}_package.json
  # 2. Stress
  curl -s http://127.0.0.1:8000/api/cases/$id/stress-lab -H "Cookie: vyapar_session_token=$SESSION_TOKEN" | jq . > public/snapshots/${id}_stress.json
  # 3. Human
  curl -s http://127.0.0.1:8000/api/cases/$id/human-decision-context -H "Cookie: vyapar_session_token=$SESSION_TOKEN" | jq . > public/snapshots/${id}_human.json
done
