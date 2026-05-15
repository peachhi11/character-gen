#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"
PYTHON_BIN="$("$ROOT_DIR/scripts/ensure_charactergen_venv.sh")"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" "$PYTHON_BIN" "$ROOT_DIR/scripts/bootstrap_local.py" --prepare --verify

cd "$ROOT_DIR"
exec "$PYTHON_BIN" main.py
