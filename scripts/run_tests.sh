#!/usr/bin/env zsh
set -euo pipefail

# Run unit tests
# Usage:
#   scripts/run_tests.sh

echo "[tests] Running python -m unittest discover"
python -m unittest discover -s tests -p "*.py"

echo "[tests] Passed"
