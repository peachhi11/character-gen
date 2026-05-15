from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from character_app.cards import CharacterRepository
from character_app.config import AppPaths
from character_app.constants import FieldId
from character_app.models import CharacterCard
from character_app.trope_engine_catalog import phase_four_activation_condition


class CharacterRepositoryEngineStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.repo = CharacterRepository(self.paths, self.paths.characters_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_payload(self, engine_type: str) -> dict:
        payload = {
            "card_id": "char_test",
            "metadata": {
                "name": "Julian",
                "archetype": "The Academic Ice-Wall",
                "engine_type": engine_type,
                "current_phase": 1,
            },
            "trope_engine_weights": {
                "lie_active": False,
                "lie_count": 0,
                "angst_meter": 1,
            },
            "origin_context": {
                "environment_type": "Academic",
                "incident_summary": "A collision over the last remaining library book.",
                "spark_token": "Coffee-stained notes.",
                "unbreakable_tether": "Assigned co-authors.",
            },
            "dialogue_nodes": {
                "phase_1_baseline": {
                    "greeting": "Hello.",
                    "body_language_descriptor": "They keep their hands folded on the desk.",
                },
                "phase_4_breaking_point": {
                    "activation_condition": "romantic_tension >= 4",
                    "dialogue_payload": "Look at me.",
                    "action_prompt": "They step into your space.",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "Let's forget it.",
                    "if_player_honest": "Even now?",
                },
            },
        }
        if engine_type == "Meet-Ugly":
            payload["trope_engine_weights"].update(
                {"rivalry_heat": 4, "repressed_desire": 1}
            )
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_desire >= 4"
        elif engine_type == "Meet-Crazy":
            payload["trope_engine_weights"].update(
                {
                    "chaotic_chemistry": 3,
                    "adrenaline_level": 4,
                    "emotional_depth": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Public spectacle"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "chaotic_chemistry >= 4"
        else:
            raise ValueError(engine_type)
        return payload

    def test_save_json_payload_validates_and_normalizes_engine_state_card(self) -> None:
        payload = self.make_payload("Meet-Crazy")
        payload["trope_engine_weights"]["chaotic_chemistry"] = 9
        payload["trope_engine_weights"]["adrenaline_level"] = -2
        del payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"]
        payload["dialogue_nodes"]["phase_4_breaking_point"]["trigger_condition"] = (
            "romantic_tension >= 4"
        )

        file_path = self.repo.save_json_payload(payload, "beatrix_engine_state")
        saved = json.loads(file_path.read_text(encoding="utf-8"))

        self.assertEqual(file_path.suffix, ".json")
        self.assertEqual(saved["trope_engine_weights"]["chaotic_chemistry"], 5)
        self.assertEqual(saved["trope_engine_weights"]["adrenaline_level"], 0)
        self.assertEqual(
            saved["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"],
            phase_four_activation_condition("Meet-Crazy"),
        )

    def test_save_json_payload_rejects_invalid_engine_state_card(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        payload["trope_engine_weights"]["rivalry_heat"] = 0
        payload["trope_engine_weights"]["lie_count"] = 1
        payload["trope_engine_weights"]["lie_active"] = True

        with self.assertRaises(RuntimeError) as error:
            self.repo.save_json_payload(payload, "broken_engine_state")

        self.assertIn("Engine-state card validation failed", str(error.exception))
        self.assertFalse(
            (self.paths.characters_dir / "broken_engine_state.json").exists()
        )

    def test_load_json_payload_validates_engine_state_card(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        del payload["metadata"]["engine_type"]
        payload["metadata"]["base_relationship"] = "Meet-Ugly"
        del payload["origin_context"]
        payload["meet_ugly_origin"] = {
            "type": "Academic",
            "incident": "Stole the final critical thesis textbook copy.",
            "spark_token": "Coffee-stained notes.",
            "tether": "Assigned co-authors.",
        }
        del payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"]
        payload["dialogue_nodes"]["phase_4_breaking_point"]["trigger_condition"] = (
            "romantic_tension >= 4"
        )

        file_path = self.paths.characters_dir / "legacy_engine.json"
        file_path.write_text(json.dumps(payload), encoding="utf-8")

        loaded = self.repo.load_json_payload(file_path)

        self.assertEqual(loaded["metadata"]["engine_type"], "Meet-Ugly")
        self.assertEqual(
            loaded["origin_context"]["incident_summary"],
            "Stole the final critical thesis textbook copy.",
        )
        self.assertEqual(
            loaded["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"],
            phase_four_activation_condition("Meet-Ugly"),
        )

    def test_load_json_payload_recovers_malformed_engine_state_from_backup(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        payload["trope_engine_weights"]["rivalry_heat"] = 2
        file_path = self.repo.save_json_payload(payload, "recover_engine_state")

        payload["trope_engine_weights"]["rivalry_heat"] = 4
        self.repo.save_json_payload(payload, "recover_engine_state")

        file_path.write_text("{ not valid json", encoding="utf-8")

        loaded = self.repo.load_json_payload(file_path)

        self.assertEqual(loaded["trope_engine_weights"]["rivalry_heat"], 2)
        restored = json.loads(file_path.read_text(encoding="utf-8"))
        self.assertEqual(restored["trope_engine_weights"]["rivalry_heat"], 2)

    def test_standard_load_recovers_malformed_character_card_from_backup(self) -> None:
        card = CharacterCard(name="Recovered Character")
        card.fields[FieldId.NAME] = "Recovered Character"
        card.fields[FieldId.DESCRIPTION] = "First version"
        file_path = self.repo.save(card, "json")

        card.fields[FieldId.DESCRIPTION] = "Second version"
        self.repo.save(card, "json")

        file_path.write_text("{ broken payload", encoding="utf-8")

        loaded = self.repo.load(str(file_path))

        self.assertEqual(loaded.fields[FieldId.DESCRIPTION], "First version")
        restored_payload = json.loads(file_path.read_text(encoding="utf-8"))
        self.assertEqual(restored_payload["data"]["description"], "First version")

    def test_load_json_payload_raises_clear_error_when_primary_and_backup_are_malformed(self) -> None:
        file_path = self.paths.characters_dir / "broken_card.json"
        backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
        file_path.write_text("{ broken", encoding="utf-8")
        backup_path.write_text("{ also broken", encoding="utf-8")

        with self.assertRaises(RuntimeError) as error:
            self.repo.load_json_payload(file_path)

        self.assertIn("malformed", str(error.exception))

    def test_standard_load_rejects_engine_state_card_in_editor_flow(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        file_path = self.paths.characters_dir / "engine_only.json"
        file_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(RuntimeError) as error:
            self.repo.load(file_path)

        self.assertIn(
            "cannot yet be opened in the standard chara-card editor",
            str(error.exception),
        )

    def test_standard_character_cards_round_trip_through_png_metadata(self) -> None:
        card = CharacterCard(name="PNG Smoke")
        card.fields[FieldId.NAME] = "PNG Smoke"
        card.fields[FieldId.DESCRIPTION] = "Standard character card payload."

        file_path = self.repo.save(card, "png")
        loaded = self.repo.load(str(file_path))

        self.assertEqual(file_path.suffix, ".png")
        self.assertEqual(loaded.name, "PNG Smoke")
        self.assertEqual(
            loaded.fields[FieldId.DESCRIPTION],
            "Standard character card payload.",
        )

    def test_engine_state_payloads_are_rejected_from_png_metadata_path(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        file_path = self.paths.characters_dir / "engine_only.png"

        import base64
        from io import BytesIO
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo

        image = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
        metadata = PngInfo()
        metadata.add_text(
            "chara",
            base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8"),
        )
        buffer = BytesIO()
        image.save(buffer, format="PNG", pnginfo=metadata)
        file_path.write_bytes(buffer.getvalue())

        with self.assertRaises(RuntimeError) as error:
            self.repo.load(str(file_path))

        self.assertIn("Engine-state character cards are JSON-only", str(error.exception))


if __name__ == "__main__":
    unittest.main()
