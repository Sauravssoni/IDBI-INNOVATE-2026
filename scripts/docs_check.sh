#!/usr/bin/env bash
set -e

echo "Starting Documentation Quality Gates..."

# 1. Forbidden term scanning (must not contain autonomous approval terms)
echo "Scanning for forbidden autonomous decision terms in docs..."
if grep -rnE "(AUTO_APPROVE|AUTO_APPROVED|AUTO_SANCTION|AI_APPROVED|FINAL_APPROVAL|APPROVED_BY_MODEL|MANUAL_REVIEW)" docs/; then
    echo "ERROR: Forbidden autonomous decision terms found in documentation!"
    echo "A system recommendation must never be stored or displayed as a final bank decision."
    exit 1
else
    echo "PASS: No forbidden autonomous decision terms found."
fi

# 2. Basic Markdown Link Check (using markdown-link-check if available, else skip or just grep for broken local links)
echo "Checking markdown links (basic local grep)..."
# Find all markdown files, look for [text](link) where link is a local file, and check if file exists.
# A basic approximation since a full AST parser isn't here. 
# For IDBI Innovate, we just ensure no glaring "TODO" links.
if grep -rni "\](TODO" docs/; then
    echo "ERROR: Found unresolved TODO links in docs!"
    exit 1
fi

echo "Documentation Quality Gates passed successfully."
