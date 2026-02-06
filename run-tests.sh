#!/usr/bin/env bash

# Simple helper script to run tests.
# Usage:
#   ./run-tests.sh           # run full test suite
#   ./run-tests.sh <target>  # run specific test file, node, or expression
#                            # e.g. ./run-tests.sh tests/test_cli_run.py::test_run_command_success

set -euo pipefail

# Prefer venv python if present
if [[ -x "./venv/bin/python" ]]; then
  PYTHON="./venv/bin/python"
else
  PYTHON="python"
fi

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python not found: $PYTHON" >&2
  exit 1
fi

# Ensure pytest is installed
if ! "$PYTHON" -m pytest --version >/dev/null 2>&1; then
  echo "pytest not found, installing into current environment..." >&2
  "$PYTHON" -m pip install pytest >/dev/null
fi

if [[ $# -eq 0 ]]; then
  # Run full suite
  exec "$PYTHON" -m pytest
else
  # Run specific target
  exec "$PYTHON" -m pytest "$@"
fi
