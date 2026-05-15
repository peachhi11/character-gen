from __future__ import annotations

import unittest

from character_app.trope_dynamic_pivot import TropeDynamicPivotParser


class AdvancedTropePivotRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = TropeDynamicPivotParser()
        self.mock_fake_relationship_session = {
            "session_id": "sess_fake_9921_run",
            "card_id": "vance_v3_asset",
            "engine_type": "Fake-Relationship",
            "current_phase": 4,
            "weights": {
                "performative_closeness": 5,
                "private_confusion": 4,
                "boundary_panic_heat": 4,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": False,
            },
            "chat_history": [{"role": "user", "content": "Stay in character."}],
        }

    def test_regression_pivot_to_secret_relationship_bounds(self) -> None:
        session_copy = dict(self.mock_fake_relationship_session)
        morphed_card, directive = self.parser.execute_catalyst_pivot(
            session_copy,
            "Secret-Relationship",
        )

        self.assertEqual(morphed_card["engine_type"], "Secret-Relationship")
        self.assertEqual(morphed_card["current_phase"], 5)

        weights = morphed_card["weights"]
        self.assertEqual(weights["fear_of_exposure"], 5)
        self.assertEqual(weights["stolen_proximity"], 5)
        self.assertTrue(weights["distance_locked"])
        self.assertEqual(weights["lie_count"], 2)
        self.assertEqual(
            morphed_card["chat_history"][0]["content"],
            "Stay in character.",
        )
        self.assertIn("[SYSTEM PROMPT DIRECTIVE CRITICAL MUTATION", directive)

    def test_regression_pivot_to_runaway_fiance_bounds(self) -> None:
        session_copy = dict(self.mock_fake_relationship_session)
        morphed_card, directive = self.parser.execute_catalyst_pivot(
            session_copy,
            "Runaway-Fiance",
        )

        self.assertEqual(morphed_card["engine_type"], "Runaway-Fiance")

        weights = morphed_card["weights"]
        self.assertEqual(weights["commitment_panic"], 5)
        self.assertEqual(weights["abandonment_guilt"], 5)
        self.assertEqual(weights["lingering_fixation_heat"], 5)
        self.assertFalse(weights["lie_active"])
        self.assertFalse(weights["distance_locked"])
        self.assertIn("INSTINCTIVE FLIGHT", directive)

    def test_rejects_non_fake_relationship_input(self) -> None:
        session_copy = dict(self.mock_fake_relationship_session)
        session_copy["engine_type"] = "Secret-Relationship"

        with self.assertRaises(ValueError) as error:
            self.parser.execute_catalyst_pivot(
                session_copy,
                "Runaway-Fiance",
            )

        self.assertIn("Expected input 'Fake-Relationship'", str(error.exception))


if __name__ == "__main__":
    unittest.main()
