from __future__ import annotations

import json
from pathlib import Path
import unittest

from character_app.analytics_validator import AnalyticsValidatorEngine


ROOT_DIR = Path(__file__).resolve().parents[1]


class AnalyticsValidatorEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = AnalyticsValidatorEngine()
        self.schema_path = (
            ROOT_DIR
            / "character_app"
            / "schemas"
            / "trope_engine_analytics_payload.schema.json"
        )

    def test_default_schema_artifact_is_valid_json(self) -> None:
        self.assertTrue(self.schema_path.exists())
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "TropeEngineAnalyticsPayload")
        self.assertIn("metrics_snapshot", schema["required"])

    def test_audit_incoming_payload_accepts_valid_packet(self) -> None:
        payload = """
        {
          "event_id": "evt_1715691720_a1b2",
          "event_type": "PHASE_SHIFT_BREAKING_POINT_4",
          "timestamp": 1715691720.52,
          "user_id": "usr_account_9921_alpha",
          "session_id": "sess_88a1b2c3",
          "metrics_snapshot": {
            "rivalry_heat": 4,
            "repressed_desire": 4,
            "angst_meter": 2,
            "lie_active": false,
            "lie_count": 0,
            "distance_locked": true
          }
        }
        """

        is_valid, message = self.validator.audit_incoming_payload(payload)

        self.assertTrue(is_valid)
        self.assertIn("PASS:", message)

    def test_audit_incoming_payload_rejects_non_json_text(self) -> None:
        is_valid, message = self.validator.audit_incoming_payload("{not-json")

        self.assertFalse(is_valid)
        self.assertIn("PARSING CRITICAL FAILURE", message)

    def test_audit_incoming_payload_rejects_out_of_bounds_metric(self) -> None:
        payload = """
        {
          "event_id": "evt_1715691720_a1b2",
          "event_type": "PHASE_SHIFT_BREAKING_POINT_4",
          "timestamp": 1715691720.52,
          "user_id": "usr_account_9921_alpha",
          "session_id": "sess_88a1b2c3",
          "metrics_snapshot": {
            "rivalry_heat": 9,
            "angst_meter": 2,
            "lie_active": false,
            "lie_count": 0,
            "distance_locked": true
          }
        }
        """

        is_valid, message = self.validator.audit_incoming_payload(payload)

        self.assertFalse(is_valid)
        self.assertIn("Field Location [metrics_snapshot -> rivalry_heat]", message)
        self.assertIn("greater than the maximum of 5", message)

    def test_audit_incoming_payload_rejects_lie_active_without_lie_count(self) -> None:
        payload = """
        {
          "event_id": "evt_1715691720_a1b2",
          "event_type": "PHASE_SHIFT_BREAKING_POINT_4",
          "timestamp": 1715691720.52,
          "user_id": "usr_account_9921_alpha",
          "session_id": "sess_88a1b2c3",
          "metrics_snapshot": {
            "angst_meter": 2,
            "lie_active": true,
            "lie_count": 0,
            "distance_locked": false
          }
        }
        """

        is_valid, message = self.validator.audit_incoming_payload(payload)

        self.assertFalse(is_valid)
        self.assertIn("SANITY TIMEOUT", message)


if __name__ == "__main__":
    unittest.main()
