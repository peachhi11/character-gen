#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$("$ROOT_DIR/scripts/ensure_charactergen_venv.sh")"

QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" "$PYTHON_BIN" "$ROOT_DIR/scripts/bootstrap_local.py" --prepare --smoke-test

echo "Bootstrap complete."
echo "Launch with: ./start.sh"
echo "Test with: ./test.sh"
