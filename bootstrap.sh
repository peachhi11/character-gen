#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export CHARACTERGEN_BOOTSTRAP_ONLY=1
exec "$ROOT_DIR/start.sh"
