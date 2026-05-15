#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_VENV_DIR="$HOME/.charactergen-venv"
VENV_DIR="${CHARACTERGEN_VENV_DIR:-$DEFAULT_VENV_DIR}"
PYTHON_BIN="$("$ROOT_DIR/scripts/ensure_charactergen_venv.sh")"

export CHARACTERGEN_TEST_RUNNER=1
export CHARACTERGEN_EXPECTED_VENV_DIR="$VENV_DIR"

QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" "$PYTHON_BIN" "$ROOT_DIR/scripts/bootstrap_local.py" --prepare --smoke-test
QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" "$PYTHON_BIN" -m unittest discover -s "$ROOT_DIR/tests" -p "test_*.py" -v
