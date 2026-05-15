from __future__ import annotations

from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from character_app.repo_asset_query_panel import run_repo_asset_query_panel_app


if __name__ == "__main__":
    raise SystemExit(run_repo_asset_query_panel_app())
