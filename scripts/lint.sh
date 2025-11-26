#!/usr/bin/env zsh
set -e

# Determine Python executable (prefer venv)
PYTHON_CMD="python3"
if [[ -f ".venv/bin/python" ]]; then
    PYTHON_CMD=".venv/bin/python"
fi

echo "[lint] Running black..."
$PYTHON_CMD -m black .

echo "[lint] Running flake8..."
$PYTHON_CMD -m flake8 .
