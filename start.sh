#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_VENV_DIR="$HOME/.charactergen-venv"
VENV_DIR="${CHARACTERGEN_VENV_DIR:-$DEFAULT_VENV_DIR}"
ENV_FILE="$ROOT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

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
  while IFS= read -r candidate; do
    if [[ "$candidate" == */* ]]; then
      if [ -x "$candidate" ]; then
        echo "$candidate"
        return 0
      fi
    elif command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
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

create_venv() {
  local candidate=""
  local resolved=""

  while IFS= read -r candidate; do
    if [[ "$candidate" == */* ]]; then
      resolved="$candidate"
      [ -x "$resolved" ] || continue
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [ -n "$resolved" ] || continue
    fi

    rm -rf "$VENV_DIR"
    if "$resolved" -m venv "$VENV_DIR"; then
      PYTHON_BIN="$resolved"
      return 0
    fi
  done < <(python_candidates)

  return 1
}

ensure_venv() {
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    create_venv
    return 0
  fi

  return 1
}

repair_venv() {
  echo "Rebuilding CharacterGen virtual environment at $VENV_DIR ..."
  create_venv
}

install_dependencies() {
  "$VENV_DIR/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
    "$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"
}

venv_health_check() {
  "$VENV_DIR/bin/python" - <<'PY'
import importlib
from importlib.metadata import version
from pathlib import Path
import sys

required = ["yaml", "requests", "PIL", "PyQt6.QtWidgets"]
for module_name in required:
    importlib.import_module(module_name)

expected_versions = {
    "PyQt6": "6.8.1",
    "PyQt6-Qt6": "6.8.2",
}
for package_name, expected_version in expected_versions.items():
    if version(package_name) != expected_version:
        raise RuntimeError(
            f"{package_name} must be {expected_version}, "
            f"found {version(package_name)}"
        )

from PyQt6.QtCore import QLibraryInfo

plugins_path = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
platforms_path = plugins_path / "platforms"
if not plugins_path.exists():
    raise RuntimeError(f"Qt plugins path missing: {plugins_path}")
if not platforms_path.exists():
    raise RuntimeError(f"Qt platforms path missing: {platforms_path}")
if not any(platforms_path.glob("libq*.dylib")):
    raise RuntimeError(f"No Qt platform plugins found in {platforms_path}")

print(f"venv-ok:{sys.version_info.major}.{sys.version_info.minor}")
PY
}

PYTHON_BIN="$(find_python || true)"

if [ -z "${PYTHON_BIN}" ]; then
  echo "Python 3.14 or 3.11 is required to run CharacterGen on this machine."
  echo "Install it first, then rerun ./start.sh"
  exit 1
fi

PREFERRED_VERSION_KEY="$(python_version_key "$PYTHON_BIN")"

venv_was_created=0
if ensure_venv; then
  venv_was_created=1
fi

if [ "$venv_was_created" -eq 0 ] && [ -x "$VENV_DIR/bin/python" ]; then
  CURRENT_VENV_VERSION_KEY="$(venv_version_key || true)"
  if [ "$CURRENT_VENV_VERSION_KEY" != "$PREFERRED_VERSION_KEY" ]; then
    repair_venv
    venv_was_created=1
  fi
fi

if [ "$venv_was_created" -eq 0 ] && ! venv_health_check >/dev/null 2>&1; then
  repair_venv
  venv_was_created=1
fi

install_dependencies

if ! venv_health_check >/dev/null 2>&1; then
  repair_venv
  install_dependencies
fi

if ! venv_health_check >/dev/null 2>&1; then
  echo "CharacterGen environment verification failed after rebuild."
  exit 1
fi

if [ "${CHARACTERGEN_BOOTSTRAP_ONLY:-0}" = "1" ]; then
  if ! "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/bootstrap_local.py" --prepare --smoke-test; then
    repair_venv
    install_dependencies
    "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/bootstrap_local.py" --prepare --smoke-test
  fi
  echo "Bootstrap complete."
  echo "Launch CharacterGen with: ./start.sh"
  exit 0
fi

if ! "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/bootstrap_local.py" --prepare --verify; then
  repair_venv
  install_dependencies
  "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/bootstrap_local.py" --prepare --verify
fi

cd "$ROOT_DIR"
exec "$VENV_DIR/bin/python" main.py
