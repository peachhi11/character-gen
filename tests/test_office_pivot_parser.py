from __future__ import annotations

import unittest

from character_app.office_pivot_parser import TropeOfficePivotParser


class OfficePivotParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = {
            "session_id": "sess_fwb_3301",
            "card_id": "maya_asset",
            "engine_type": "Friends-Benefits",
            "current_phase": 4,
            "weights": {
                "platonic_baseline_trust": 4,
                "contractual_intimacy": 4,
                "private_romantic_fixation": 3,
                "boundary_panic_heat": 4,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": False,
            },
            "chat_history": [{"role": "user", "content": "We were fine before the promotion."}],
        }

    def test_pivot_fwb_to_office_boss_clamps_and_retargets_weights(self) -> None:
        morphed, directive = TropeOfficePivotParser.pivot_fwb_to_office_boss(self.session)

        self.assertEqual(morphed["engine_type"], "Boardroom-Parity")
        self.assertEqual(morphed["current_phase"], 2)
        self.assertEqual(morphed["weights"]["promotion_rivalry_heat"], 5)
        self.assertEqual(morphed["weights"]["favoritism_paranoia"], 5)
        self.assertEqual(morphed["weights"]["private_fixation"], 3)
        self.assertTrue(morphed["weights"]["lie_active"])
        self.assertEqual(morphed["weights"]["lie_count"], 2)
        self.assertTrue(morphed["weights"]["distance_locked"])
        self.assertIn("BOARDROOM PARITY", directive)
        self.assertEqual(
            morphed["chat_history"][0]["content"],
            "We were fine before the promotion.",
        )

    def test_pivot_rejects_wrong_source_engine(self) -> None:
        bad_session = dict(self.session)
        bad_session["engine_type"] = "Office-Benefits"

        with self.assertRaises(ValueError) as error:
            TropeOfficePivotParser.pivot_fwb_to_office_boss(bad_session)

        self.assertIn("Expected 'Friends-Benefits'", str(error.exception))


if __name__ == "__main__":
    unittest.main()
