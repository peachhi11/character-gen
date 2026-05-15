#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from character_app.card_schema_validation import CharacterCardValidator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an engine-state character card JSON payload."
    )
    parser.add_argument("json_file", type=Path, help="Path to the JSON payload to validate.")
    args = parser.parse_args()

    payload = args.json_file.read_text(encoding="utf-8")
    result = CharacterCardValidator().validate_card_json(payload)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
