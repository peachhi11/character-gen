from __future__ import annotations

import unittest

from character_app.runtime_chat import RuntimeChatService
from character_app.runtime_state import EngineStateCard


class StubAPIClient:
    def generate_chat(
        self,
        *,
        system_prompt: str,
        chat_history: list[dict[str, str]],
        user_message: str,
    ) -> str:
        return "stub response"


class RuntimeChatServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RuntimeChatService(StubAPIClient())
        self.base_payload = {
            "card_id": "vance_v3_asset",
            "metadata": {
                "name": "Julian Vance",
                "archetype": "The Academic Ice-Wall",
                "engine_type": "Meet-Ugly",
                "current_phase": 1,
            },
            "trope_engine_weights": {
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
                "phase_1_baseline": {
                    "greeting": "Oh, look. The resident expert arrived.",
                    "body_language_descriptor": "They do not look up from their laptop, but their typing speed accelerates sharply.",
                },
                "phase_4_breaking_point": {
                    "activation_condition": "romantic_tension >= 4",
                    "dialogue_payload": "I don't hate you. I fight with you because it's the only time you look at me with absolute focus.",
                    "action_prompt": "They step directly into your space.",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "A tactical error. Let's forget it.",
                    "if_player_honest": "Even now? When there's nothing left to hide behind?",
                },
            },
        }

    def test_build_runtime_card_overlays_live_session_state(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        session.current_phase = 4
        session.weights["rivalry_heat"] = 5
        session.weights["romantic_tension"] = 4

        runtime_card = self.service.build_runtime_card(self.base_payload, session)

        self.assertEqual(runtime_card["metadata"]["current_phase"], 4)
        self.assertEqual(runtime_card["trope_engine_weights"]["rivalry_heat"], 5)
        self.assertEqual(runtime_card["trope_engine_weights"]["romantic_tension"], 4)

    def test_compile_runtime_prompt_normalizes_live_lie_state(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        session.weights["lie_active"] = True
        session.weights["lie_count"] = 0
        session.weights["rivalry_heat"] = 0

        prompt = self.service.compile_runtime_prompt(self.base_payload, session)

        self.assertIn("lie_active: True", prompt)
        self.assertIn("lie_count: 1", prompt)
        self.assertIn("rivalry_heat: 1", prompt)


if __name__ == "__main__":
    unittest.main()
