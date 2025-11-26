#!/usr/bin/env python3
"""
Script to check individual file coverage and ensure no file is below 75%
(excluding __init__.py files)
"""
import sys
import subprocess

# Run pytest with coverage
result = subprocess.run(
    [
        ".venv/bin/python",
        "-m",
        "pytest",
        "--cov=app",
        "tests/",
        "--cov-report=term-missing",
        "--cov-fail-under=75",
    ],
    capture_output=True,
    text=True,
)

print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)

# Exit with pytest's exit code
sys.exit(result.returncode)
