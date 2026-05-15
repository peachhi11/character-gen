from __future__ import annotations

import io
import unittest

from PIL import Image

from character_app.card_format_conversion import convert_v2_to_v3_with_engine
from character_app.png_metadata_engine import PNGMetadataEngine


class PNGMetadataEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PNGMetadataEngine()

    def make_base_image_bytes(self) -> bytes:
        image = Image.new("RGBA", (64, 64), (255, 0, 0, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def make_v2_payload(self) -> dict:
        return {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": "Julian Vance",
                "description": "An exacting academic rival with polished edges.",
                "personality": "The Academic Ice-Wall",
                "scenario": "Late-night library archive standoff.",
                "first_mes": "Oh, look. The resident expert arrived. Try not to break anything today.",
                "mes_example": "They keep their posture controlled and cold until something cracks.",
                "extensions": {
                    "trope_engine": {
                        "engine_type": "Meet-Ugly",
                        "current_phase": 4,
                        "weights": {
                            "rivalry_heat": 4,
                            "repressed_desire": 3,
                            "angst_meter": 2,
                            "lie_active": True,
                            "lie_count": 1,
                            "distance_locked": True,
                        },
                        "origin_context": {
                            "environment_type": "University Library Archives",
                            "incident_summary": "Stole the final critical thesis textbook copy straight out of the player's hands.",
                            "spark_token": "The shared research notes with coffee stains across the margins.",
                            "unbreakable_tether": "Assigned as co-authors on the career-making publication."
                        },
                        "dialogue_nodes": {
                            "phase_4_breaking_point": {
                                "activation_condition": "romantic_tension >= 4",
                                "dialogue_payload": "I don't hate you. I fight with you because it's the only time you look at me with absolute focus.",
                                "action_prompt": "They step directly into your space."
                            },
                            "phase_5_hangover_crisis": {
                                "if_player_lied": "A tactical error driven by cortisol levels. Let's forget it.",
                                "if_player_honest": "Even now? When there's nothing left to hide behind?"
                            }
                        }
                    }
                }
            }
        }

    def make_canonical_engine_state(self) -> dict:
        return {
            "card_id": "char_test",
            "metadata": {
                "name": "Julian Vance",
                "archetype": "The Academic Ice-Wall",
                "engine_type": "Meet-Ugly",
                "current_phase": 4,
            },
            "trope_engine_weights": {
                "rivalry_heat": 4,
                "repressed_desire": 3,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": True,
            },
            "origin_context": {
                "environment_type": "University Library Archives",
                "incident_summary": "Stole the final critical thesis textbook copy straight out of the player's hands.",
                "spark_token": "The shared research notes with coffee stains across the margins.",
                "unbreakable_tether": "Assigned as co-authors on the career-making publication.",
            },
            "dialogue_nodes": {
                "phase_1_baseline": {
                    "greeting": "Oh, look. The resident expert arrived. Try not to break anything today.",
                    "body_language_descriptor": "They keep their posture controlled and cold until something cracks.",
                },
                "phase_4_breaking_point": {
                    "activation_condition": "romantic_tension >= 4",
                    "dialogue_payload": "I don't hate you. I fight with you because it's the only time you look at me with absolute focus.",
                    "action_prompt": "They step directly into your space.",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "A tactical error driven by cortisol levels. Let's forget it.",
                    "if_player_honest": "Even now? When there's nothing left to hide behind?",
                },
            },
        }

    def test_round_trips_v2_payload_through_png_metadata(self) -> None:
        base = self.make_base_image_bytes()
        payload = self.make_v2_payload()

        png_bytes = self.engine.inject_card_data(base, payload)
        extracted = self.engine.extract_card_data(png_bytes)

        self.assertEqual(extracted["spec"], "chara_card_v2")
        self.assertEqual(
            extracted["data"]["extensions"]["trope_engine"]["engine_type"],
            "Meet-Ugly",
        )

    def test_round_trips_v3_payload_through_png_metadata(self) -> None:
        base = self.make_base_image_bytes()
        payload = convert_v2_to_v3_with_engine(self.make_v2_payload())

        png_bytes = self.engine.inject_card_data(base, payload)
        extracted = self.engine.extract_card_data(png_bytes)

        self.assertEqual(extracted["spec"], "chara_card_v3")
        self.assertEqual(
            extracted["extensions"]["trope_engine"]["engine_type"],
            "Meet-Ugly",
        )

    def test_rejects_raw_engine_state_payload_for_png_embedding(self) -> None:
        with self.assertRaises(RuntimeError) as error:
            self.engine.inject_card_data(
                self.make_base_image_bytes(), self.make_canonical_engine_state()
            )

        self.assertIn("JSON-only", str(error.exception))


if __name__ == "__main__":
    unittest.main()
