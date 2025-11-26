#!/usr/bin/env zsh
set -euo pipefail

# Run unit tests
# Usage:
#   scripts/run_tests.sh

echo "[tests] Running pytest..."
# Determine Python executable (prefer venv)
PYTHON_CMD="python3"
if [[ -f ".venv/bin/python" ]]; then
    PYTHON_CMD=".venv/bin/python"
fi

echo "[tests] Running pytest with coverage..."
$PYTHON_CMD -m pytest --cov=app tests/ --cov-fail-under=75

echo "[tests] Passed with coverage >= 75%"
