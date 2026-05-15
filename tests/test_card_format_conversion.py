from __future__ import annotations

import json
from pathlib import Path
import unittest

from character_app.card_format_conversion import (
    convert_v2_to_v3_with_engine,
    extract_trope_engine_card,
    wrap_trope_engine_card_as_v3,
)


ROOT_DIR = Path(__file__).resolve().parents[1]


class CardFormatConversionTest(unittest.TestCase):
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
                "alternate_greetings": ["You again."],
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

    def test_convert_v2_to_v3_with_engine_preserves_extension(self) -> None:
        v2_payload = self.make_v2_payload()
        v3_payload = convert_v2_to_v3_with_engine(v2_payload)

        self.assertEqual(v3_payload["spec"], "chara_card_v3")
        self.assertEqual(v3_payload["spec_version"], "3.0")
        self.assertEqual(v3_payload["name"], "Julian Vance")
        self.assertEqual(
            v3_payload["extensions"]["trope_engine"]["engine_type"], "Meet-Ugly"
        )
        self.assertEqual(v3_payload["alternate_greetings"], ["You again."])

    def test_extract_trope_engine_card_from_v2_payload(self) -> None:
        canonical = extract_trope_engine_card(self.make_v2_payload())

        self.assertEqual(canonical["metadata"]["name"], "Julian Vance")
        self.assertEqual(canonical["metadata"]["archetype"], "The Academic Ice-Wall")
        self.assertEqual(canonical["metadata"]["engine_type"], "Meet-Ugly")
        self.assertEqual(
            canonical["dialogue_nodes"]["phase_1_baseline"]["greeting"],
            "Oh, look. The resident expert arrived. Try not to break anything today.",
        )
        self.assertIn("body_language_descriptor", canonical["dialogue_nodes"]["phase_1_baseline"])

    def test_extract_trope_engine_card_from_v3_payload(self) -> None:
        v3_payload = convert_v2_to_v3_with_engine(self.make_v2_payload())
        canonical = extract_trope_engine_card(v3_payload)

        self.assertEqual(canonical["metadata"]["engine_type"], "Meet-Ugly")
        self.assertEqual(
            canonical["origin_context"]["environment_type"],
            "University Library Archives",
        )

    def test_wrap_trope_engine_card_as_v3_accepts_canonical_payload(self) -> None:
        canonical = extract_trope_engine_card(self.make_v2_payload())

        wrapped = wrap_trope_engine_card_as_v3(canonical)

        self.assertEqual(wrapped["spec"], "chara_card_v3")
        self.assertEqual(wrapped["spec_version"], "3.0")
        self.assertEqual(wrapped["name"], "Julian Vance")
        self.assertEqual(
            wrapped["extensions"]["trope_engine"]["engine_type"], "Meet-Ugly"
        )
        self.assertEqual(
            wrapped["extensions"]["trope_engine"]["origin_context"][
                "environment_type"
            ],
            "University Library Archives",
        )

    def test_schema_artifacts_are_valid_json(self) -> None:
        for schema_name in (
            "character_card_v2_with_trope_engine.schema.json",
            "character_card_v3_with_trope_engine.schema.json",
        ):
            schema = json.loads(
                (
                    ROOT_DIR
                    / "character_app"
                    / "schemas"
                    / schema_name
                ).read_text(encoding="utf-8")
            )
            self.assertIn("title", schema)


if __name__ == "__main__":
    unittest.main()
