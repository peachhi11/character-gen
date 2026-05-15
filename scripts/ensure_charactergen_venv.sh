#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_VENV_DIR="$HOME/.charactergen-venv"
VENV_DIR="${CHARACTERGEN_VENV_DIR:-$DEFAULT_VENV_DIR}"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
STAMP_FILE="$VENV_DIR/.charactergen-requirements.sha256"

log() {
  printf '[venv] %s\n' "$*" >&2
}

python_candidates() {
  cat <<'EOF'
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14
/opt/homebrew/bin/python3.14
python3.14
/opt/homebrew/bin/python3.11
python3.11
EOF
}

find_python() {
  local candidate=""
  local resolved=""

  while IFS= read -r candidate; do
    if [[ "$candidate" == */* ]]; then
      [ -x "$candidate" ] || continue
      printf '%s\n' "$candidate"
      return 0
    fi

    resolved="$(command -v "$candidate" 2>/dev/null || true)"
    [ -n "$resolved" ] || continue
    printf '%s\n' "$resolved"
    return 0
  done < <(python_candidates)

  return 1
}

python_version_key() {
  "$1" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
}

venv_version_key() {
  "$VENV_DIR/bin/python" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
}

requirements_hash() {
  shasum -a 256 "$REQUIREMENTS_FILE" | awk '{print $1}'
}

create_venv() {
  local python_bin="$1"

  log "creating CharacterGen venv at $VENV_DIR"
  rm -rf "$VENV_DIR"
  "$python_bin" -m venv "$VENV_DIR"
}

install_dependencies() {
  log "installing CharacterGen dependencies"
  "$VENV_DIR/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
    "$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS_FILE" >&2
  requirements_hash > "$STAMP_FILE"
}

venv_health_check() {
  "$VENV_DIR/bin/python" - <<'PY'
import importlib
from importlib.metadata import version
from pathlib import Path

required_modules = ("yaml", "requests", "PIL", "PyQt6.QtWidgets")
for module_name in required_modules:
    importlib.import_module(module_name)

expected_versions = {
    "PyQt6": "6.8.1",
    "PyQt6-Qt6": "6.8.2",
}
for package_name, expected_version in expected_versions.items():
    actual_version = version(package_name)
    if actual_version != expected_version:
        raise RuntimeError(
            f"{package_name} must be {expected_version}, found {actual_version}"
        )

from PyQt6.QtCore import QLibraryInfo

plugins_path = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
platforms_path = plugins_path / "platforms"
if not platforms_path.exists():
    raise RuntimeError(f"Qt platforms path missing: {platforms_path}")
if not any(platforms_path.glob("libq*.dylib")):
    raise RuntimeError(f"No Qt platform plugins found in {platforms_path}")
PY
}

if [ ! -f "$REQUIREMENTS_FILE" ]; then
  echo "Missing requirements file: $REQUIREMENTS_FILE" >&2
  exit 1
fi

PYTHON_BIN="$(find_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3.14 or 3.11 is required for CharacterGen." >&2
  exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  create_venv "$PYTHON_BIN"
elif [ "$(venv_version_key || true)" != "$(python_version_key "$PYTHON_BIN")" ]; then
  create_venv "$PYTHON_BIN"
fi

EXPECTED_HASH="$(requirements_hash)"
CURRENT_HASH=""
if [ -f "$STAMP_FILE" ]; then
  CURRENT_HASH="$(cat "$STAMP_FILE")"
fi

if [ "$CURRENT_HASH" != "$EXPECTED_HASH" ]; then
  install_dependencies
elif ! venv_health_check >/dev/null 2>&1; then
  install_dependencies
fi

if ! venv_health_check >/dev/null 2>&1; then
  create_venv "$PYTHON_BIN"
  install_dependencies
fi

if ! venv_health_check >/dev/null 2>&1; then
  echo "CharacterGen venv verification failed after rebuild." >&2
  exit 1
fi

printf '%s\n' "$VENV_DIR/bin/python"
