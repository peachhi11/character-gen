from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_PATH = (
    Path(__file__).resolve().parent
    / "schemas"
    / "trope_engine_analytics_payload.schema.json"
)


class AnalyticsValidatorEngine:
    def __init__(self, schema_dict: dict[str, Any] | None = None) -> None:
        self.schema_dict = schema_dict or self.load_default_schema()
        Draft202012Validator.check_schema(self.schema_dict)
        self.validator = Draft202012Validator(self.schema_dict)

    @staticmethod
    def load_default_schema() -> dict[str, Any]:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def audit_incoming_payload(
        self, raw_json_payload: str | dict[str, Any]
    ) -> tuple[bool, str]:
        if isinstance(raw_json_payload, str):
            try:
                data = json.loads(raw_json_payload)
            except json.JSONDecodeError:
                return (
                    False,
                    "PARSING CRITICAL FAILURE: Inbound text is not valid JSON format.",
                )
        else:
            data = json.loads(json.dumps(raw_json_payload))

        errors = sorted(
            self.validator.iter_errors(data),
            key=lambda error: list(error.path),
        )
        if errors:
            error_messages: list[str] = []
            for error in errors:
                path = " -> ".join(str(part) for part in error.path) or "root"
                error_messages.append(f"Field Location [{path}]: {error.message}")
            return False, "VALIDATION EXCEPTION: " + " | ".join(error_messages)

        metrics = data.get("metrics_snapshot", {})
        if metrics.get("lie_count", 0) == 0 and metrics.get("lie_active") is True:
            return (
                False,
                "SANITY TIMEOUT: 'lie_active' flag cannot be True while 'lie_count' is 0.",
            )

        return (
            True,
            "PASS: Inbound event packet matches analytics data contract specifications.",
        )
