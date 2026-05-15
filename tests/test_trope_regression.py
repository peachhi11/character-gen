from __future__ import annotations

import unittest

from character_app.card_format_conversion import extract_trope_engine_card
from character_app.dialogue_triggers import DialogueTriggerEngine
from character_app.live_chat_state import LiveChatLogAnalyzer
from scripts.seed_trope_engine_png_fixtures import fixture_payloads


def _fixture_map() -> dict[str, dict]:
    mapped: dict[str, dict] = {}
    for payload in fixture_payloads():
        mapped[payload["id"]] = payload
    return mapped


class TropeEngineRegressionTestSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = LiveChatLogAnalyzer()
        self.trigger_system = DialogueTriggerEngine()
        self.fixtures = _fixture_map()

    def test_meet_cute_romantic_awareness_escalation(self) -> None:
        ccv3_card = self.fixtures["ccv3_fix_001_cute"]
        canonical = extract_trope_engine_card(ccv3_card)
        session_state = {
            "platonic_trust": 4,
            "romantic_awareness": 1,
            "fear_of_loss": 3,
            "angst_meter": 0,
            "lie_active": False,
        }

        updated_weights, signal = self.analyzer.analyze_message_turn(
            "I place my hand over yours on the desk, refusing to pull away.",
            "Her breath catches completely. She flushes, staring down at your lips in a long pause.",
            session_state,
        )

        self.assertEqual(canonical["metadata"]["engine_type"], "Meet-Cute")
        self.assertEqual(updated_weights["romantic_awareness"], 2)
        self.assertEqual(updated_weights["platonic_trust"], 4)
        self.assertNotIn("rivalry_heat", updated_weights)
        self.assertEqual(signal, "MAINTAIN_STATE")

    def test_meet_ugly_breaking_point_actuation(self) -> None:
        ccv3_card = self.fixtures["ccv3_fix_002_ugly"]
        session_state = {
            "current_phase": 3,
            "weights": {
                "rivalry_heat": 4,
                "repressed_desire": 4,
                "angst_meter": 2,
                "lie_active": False,
                "lie_count": 0,
            },
        }

        signal, payload = self.trigger_system.evaluate_all_active_triggers(
            ccv3_card, session_state
        )

        self.assertEqual(signal, "EXECUTE_PHASE_4_BREAKING_POINT")
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertTrue(payload["dialogue"].startswith("I fight with you"))

    def test_meet_crazy_adrenaline_crash_to_denial_mask(self) -> None:
        ccv3_card = self.fixtures["ccv3_fix_003_crazy"]
        canonical = extract_trope_engine_card(ccv3_card)
        session_state = {
            "chaotic_chemistry": 4,
            "adrenaline_level": 0,
            "emotional_depth": 1,
            "angst_meter": 1,
            "lie_active": False,
            "lie_count": 0,
            "current_phase": 4,
        }

        updated_weights, signal = self.analyzer.analyze_message_turn(
            "Look, last night was just a mistake. It was just the adrenaline talking. Let's forget it.",
            "Roxie blinks, her smirk instantly dropping. 'Right. A total mistake. Fine.'",
            session_state,
        )

        self.assertEqual(canonical["metadata"]["engine_type"], "Meet-Crazy")
        self.assertTrue(updated_weights["lie_active"])
        self.assertEqual(updated_weights["lie_count"], 1)
        self.assertGreater(updated_weights["angst_meter"], 1)
        self.assertEqual(signal, "TRIGGER_HANGOVER_CRISIS_LIE")

    def test_forced_proximity_claustrophobia_stress_clamping(self) -> None:
        ccv3_card = self.fixtures["ccv3_fix_004_forced"]
        canonical = extract_trope_engine_card(ccv3_card)
        session_state = {
            "confinement_stress": 5,
            "hostile_friction_heat": 4,
            "proximity_awareness_acceleration": 3,
            "angst_meter": 2,
            "distance_locked": True,
            "current_phase": 2,
        }

        updated_weights, signal = self.analyzer.analyze_message_turn(
            "The air in here is getting so hot. We're trapped. I feel completely boxed in.",
            "He stands still, his shoulder pinned right against yours in the dim light box shadow.",
            session_state,
        )

        self.assertEqual(canonical["metadata"]["engine_type"], "Forced-Proximity")
        self.assertEqual(updated_weights["confinement_stress"], 5)
        self.assertLessEqual(updated_weights["confinement_stress"], 5)
        self.assertEqual(updated_weights["proximity_awareness_acceleration"], 4)
        self.assertEqual(signal, "FORCE_PHASE_4_BREAKING_POINT")


if __name__ == "__main__":
    unittest.main()
