from __future__ import annotations

import unittest

from character_app.live_chat_state import LiveChatLogAnalyzer


class LiveChatStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = LiveChatLogAnalyzer()

    def test_spiking_tension_forces_phase_four(self) -> None:
        state = {
            "romantic_tension": 3,
            "angst_meter": 1,
            "lie_active": False,
            "lie_count": 0,
            "current_phase": 3,
        }

        updated, signal = self.analyzer.analyze_message_turn(
            "I step closer and refuse to break eye contact.",
            "Their breath catches and their gaze drops to your lips.",
            state,
        )

        self.assertEqual(updated["romantic_tension"], 4)
        self.assertEqual(updated["current_phase"], 4)
        self.assertEqual(signal, "FORCE_PHASE_4_BREAKING_POINT")

    def test_defensive_language_triggers_lie_state(self) -> None:
        state = {
            "romantic_tension": 4,
            "angst_meter": 1,
            "lie_active": False,
            "lie_count": 0,
            "current_phase": 4,
        }

        updated, signal = self.analyzer.analyze_message_turn(
            "It was a mistake, an accident, nothing. Forget it.",
            "They go perfectly still.",
            state,
        )

        self.assertTrue(updated["lie_active"])
        self.assertEqual(updated["lie_count"], 1)
        self.assertEqual(updated["angst_meter"], 3)
        self.assertEqual(signal, "TRIGGER_HANGOVER_CRISIS_LIE")

    def test_vulnerability_language_shatters_active_lie(self) -> None:
        state = {
            "romantic_tension": 4,
            "emotional_depth": 1,
            "angst_meter": 4,
            "lie_active": True,
            "lie_count": 1,
            "current_phase": 4,
        }

        updated, signal = self.analyzer.analyze_message_turn(
            "Honestly, I'm scared, but I love you and I need the truth.",
            "Their whole expression breaks open.",
            state,
        )

        self.assertFalse(updated["lie_active"])
        self.assertEqual(updated["angst_meter"], 1)
        self.assertEqual(updated["emotional_depth"], 4)
        self.assertEqual(signal, "TRIGGER_LIE_SHATTERED_CLIMAX")

    def test_meet_cute_state_can_increment_romantic_awareness(self) -> None:
        state = {
            "romantic_awareness": 1,
            "platonic_trust": 4,
            "fear_of_loss": 3,
            "angst_meter": 0,
            "lie_active": False,
        }

        updated, signal = self.analyzer.analyze_message_turn(
            "I put my hand over yours and stay there.",
            "Her breath catches and her gaze drops to your lips.",
            state,
        )

        self.assertEqual(updated["romantic_awareness"], 2)
        self.assertEqual(updated["platonic_trust"], 4)
        self.assertEqual(signal, "MAINTAIN_STATE")

    def test_forced_proximity_state_clamps_confinement_stress(self) -> None:
        state = {
            "confinement_stress": 5,
            "hostile_friction_heat": 4,
            "proximity_awareness_acceleration": 2,
            "distance_locked": True,
            "angst_meter": 1,
        }

        updated, signal = self.analyzer.analyze_message_turn(
            "The air is hot and we're trapped in here.",
            "Their shoulder stays close to yours against the wall.",
            state,
        )

        self.assertEqual(updated["confinement_stress"], 5)
        self.assertEqual(updated["proximity_awareness_acceleration"], 3)
        self.assertEqual(signal, "MAINTAIN_STATE")


if __name__ == "__main__":
    unittest.main()
