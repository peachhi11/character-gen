#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from character_app.config import AppPaths
from character_app.prompt_testing import (
    load_cases,
    load_prompt_set,
    render_case_prompts,
    run_live_case,
    validate_rendered_prompts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run offline or live prompt tests against CharacterGen prompt sets."
    )
    parser.add_argument(
        "--cases-dir",
        default=str(ROOT_DIR / "tests" / "prompt_cases"),
        help="Directory containing prompt test case JSON files.",
    )
    parser.add_argument(
        "--fixtures-dir",
        default=str(ROOT_DIR / "tests" / "fixtures"),
        help="Directory containing prompt test fixtures such as reference cards.",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Limit execution to one or more named cases.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the configured model and validate actual generated outputs.",
    )
    parser.add_argument(
        "--report",
        help="Optional path to write a JSON report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = AppPaths(root=ROOT_DIR)
    cases_dir = Path(args.cases_dir)
    fixtures_dir = Path(args.fixtures_dir)
    selected = set(args.case)
    cases = [
        case for case in load_cases(cases_dir) if not selected or case.name in selected
    ]
    if not cases:
        print("No prompt test cases matched.")
        return 1

    report: list[dict[str, object]] = []
    has_failures = False

    for case in cases:
        prompt_set = load_prompt_set(paths, case.prompt_library, case.prompt_set)
        rendered = render_case_prompts(paths, case, fixtures_dir)
        issues = validate_rendered_prompts(case, prompt_set, rendered)
        entry: dict[str, object] = {
            "case": case.name,
            "mode": "live" if args.live else "offline",
            "prompt_library": case.prompt_library,
            "prompt_set": case.prompt_set,
            "render_issues": issues,
        }
        print(f"[case] {case.name} ({case.prompt_library}:{case.prompt_set})")
        if issues:
            has_failures = True
            for issue in issues:
                print(f"  render issue: {issue}")
        else:
            print("  render checks: ok")

        if args.live:
            outputs, live_issues = run_live_case(paths, case, fixtures_dir)
            entry["live_issues"] = live_issues
            entry["outputs"] = {field.value: text for field, text in outputs.items()}
            if live_issues:
                has_failures = True
                for issue in live_issues:
                    print(f"  live issue: {issue}")
            else:
                print("  live checks: ok")

        report.append(entry)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
