#!/bin/bash
CASES=$(cat public/snapshots/cases_list.json | jq -r '.[].id')
for id in $CASES; do
  echo "Downloading for $id"
  # 1. Package
  curl -s http://127.0.0.1:8000/api/cases/$id/decision-package -b cookies.txt | jq . > public/snapshots/${id}_package.json
  # 2. Stress
  curl -s http://127.0.0.1:8000/api/cases/$id/stress-lab -b cookies.txt | jq . > public/snapshots/${id}_stress.json
  # 3. Human
  curl -s http://127.0.0.1:8000/api/cases/$id/human-decision-context -b cookies.txt | jq . > public/snapshots/${id}_human.json
done
