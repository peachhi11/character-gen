from __future__ import annotations

import unittest

from character_app.dialogue_triggers import DialogueTriggerEngine


class DialogueTriggerEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DialogueTriggerEngine()
        self.payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "vance_v3_asset",
            "name": "Julian Vance",
            "first_mes": "Oh, look. The resident expert arrived.",
            "extensions": {
                "trope_engine": {
                    "engine_type": "Meet-Ugly",
                    "current_phase": 1,
                    "weights": {
                        "rivalry_heat": 4,
                        "repressed_desire": 2,
                        "angst_meter": 1,
                        "lie_active": False,
                        "lie_count": 0,
                        "distance_locked": False,
                    },
                    "origin_context": {
                        "environment_type": "University Library Archives",
                        "incident_summary": "Stole the final critical thesis textbook copy.",
                        "spark_token": "The research notes with coffee stains.",
                        "unbreakable_tether": "Assigned as co-authors on the publication.",
                    },
                    "dialogue_nodes": {
                        "phase_4_breaking_point": {
                            "activation_condition": "repressed_desire >= 4",
                            "dialogue_payload": "I am utterly sick of pretending I don't want your complete attention.",
                            "action_prompt": "He steps directly into your space, slamming his laptop shut.",
                        },
                        "phase_5_hangover_crisis": {
                            "if_player_lied": "A tactical error driven by elevated cortisol levels. Let's act like professionals.",
                            "if_player_honest": "Don't look back down at your papers. You have had all of my focus from the start.",
                        },
                    },
                }
            },
        }

    def test_evaluate_condition_string_supports_numeric_thresholds(self) -> None:
        self.assertTrue(
            self.engine.evaluate_condition_string(
                "repressed_desire >= 4",
                {"repressed_desire": 4},
            )
        )
        self.assertFalse(
            self.engine.evaluate_condition_string(
                "repressed_desire >= 4",
                {"repressed_desire": 3},
            )
        )

    def test_evaluate_condition_string_rejects_invalid_expression(self) -> None:
        self.assertFalse(
            self.engine.evaluate_condition_string(
                "repressed_desire => 4",
                {"repressed_desire": 4},
            )
        )

    def test_evaluate_condition_string_supports_and_routes(self) -> None:
        self.assertTrue(
            self.engine.evaluate_condition_string(
                "nostalgic_relapse_drive >= 5 and time_gap_divergence <= 1",
                {"nostalgic_relapse_drive": 5, "time_gap_divergence": 1},
            )
        )
        self.assertFalse(
            self.engine.evaluate_condition_string(
                "nostalgic_relapse_drive >= 5 and time_gap_divergence <= 1",
                {"nostalgic_relapse_drive": 5, "time_gap_divergence": 2},
            )
        )

    def test_evaluate_condition_string_supports_or_routes(self) -> None:
        self.assertTrue(
            self.engine.evaluate_condition_string(
                "romantic_tension >= 4 or romantic_awareness >= 4",
                {"romantic_tension": 2, "romantic_awareness": 4},
            )
        )
        self.assertFalse(
            self.engine.evaluate_condition_string(
                "romantic_tension >= 4 or romantic_awareness >= 4",
                {"romantic_tension": 2, "romantic_awareness": 3},
            )
        )

    def test_evaluate_condition_string_supports_mixed_or_and_routes(self) -> None:
        condition = (
            "guilt_conversion_index >= 4 or moral_crisis_heat == 5 and "
            "guilt_conversion_index >= 3"
        )
        self.assertTrue(
            self.engine.evaluate_condition_string(
                condition,
                {"moral_crisis_heat": 5, "guilt_conversion_index": 3},
            )
        )
        self.assertFalse(
            self.engine.evaluate_condition_string(
                condition,
                {"moral_crisis_heat": 4, "guilt_conversion_index": 3},
            )
        )

    def test_phase_four_trigger_fires_when_threshold_is_met(self) -> None:
        signal, payload = self.engine.evaluate_all_active_triggers(
            self.payload,
            {
                "current_phase": 1,
                "weights": {
                    "rivalry_heat": 4,
                    "repressed_desire": 4,
                    "lie_active": False,
                    "lie_count": 0,
                },
            },
        )

        self.assertEqual(signal, "EXECUTE_PHASE_4_BREAKING_POINT")
        self.assertIsNotNone(payload)
        self.assertIn("complete attention", payload["dialogue"])

    def test_phase_five_denial_route_fires_for_active_lie(self) -> None:
        signal, payload = self.engine.evaluate_all_active_triggers(
            self.payload,
            {
                "current_phase": 4,
                "weights": {
                    "rivalry_heat": 4,
                    "repressed_desire": 4,
                    "lie_active": True,
                    "lie_count": 1,
                },
            },
        )

        self.assertEqual(signal, "EXECUTE_PHASE_5_HANGOVER_CRISIS_DENIAL")
        self.assertIsNotNone(payload)
        self.assertIn("tactical error", payload["dialogue"])

    def test_phase_five_vulnerable_route_fires_without_lie_state(self) -> None:
        signal, payload = self.engine.evaluate_all_active_triggers(
            self.payload,
            {
                "current_phase": 4,
                "weights": {
                    "rivalry_heat": 4,
                    "repressed_desire": 4,
                    "lie_active": False,
                    "lie_count": 0,
                },
            },
        )

        self.assertEqual(signal, "EXECUTE_PHASE_5_HANGOVER_CRISIS_VULNERABLE")
        self.assertIsNotNone(payload)
        self.assertIn("all of my focus", payload["dialogue"])

    def test_phase_four_trigger_fires_for_compound_activation_condition(self) -> None:
        compound_payload = {
            **self.payload,
            "extensions": {
                "trope_engine": {
                    **self.payload["extensions"]["trope_engine"],
                    "dialogue_nodes": {
                        **self.payload["extensions"]["trope_engine"]["dialogue_nodes"],
                        "phase_4_breaking_point": {
                            "activation_condition": "nostalgic_relapse_drive >= 5 and time_gap_divergence <= 1",
                            "dialogue_payload": "The last decade just vanished.",
                            "action_prompt": "They catch your arm before you can leave.",
                        },
                    },
                }
            },
        }

        signal, payload = self.engine.evaluate_all_active_triggers(
            compound_payload,
            {
                "current_phase": 1,
                "weights": {
                    "nostalgic_relapse_drive": 5,
                    "time_gap_divergence": 1,
                    "lie_active": True,
                    "lie_count": 1,
                },
            },
        )

        self.assertEqual(signal, "EXECUTE_PHASE_4_BREAKING_POINT")
        self.assertIsNotNone(payload)
        self.assertIn("last decade", payload["dialogue"])


if __name__ == "__main__":
    unittest.main()
