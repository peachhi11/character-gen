from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from character_app.card_format_conversion import extract_trope_engine_card
from character_app.card_schema_validation import CharacterCardValidator
from character_app.png_metadata_engine import PNGMetadataEngine
from scripts.seed_trope_engine_png_fixtures import seed_fixture_directory


class SeedTropeEngineFixturesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.metadata_engine = PNGMetadataEngine()
        self.validator = CharacterCardValidator()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_seed_fixture_directory_writes_json_and_png_for_all_cards(self) -> None:
        written = seed_fixture_directory(self.output_dir)

        json_files = sorted(self.output_dir.glob("*_v3.json"))
        png_files = sorted(self.output_dir.glob("*_v3.png"))

        self.assertEqual(len(written), 8)
        self.assertEqual(len(json_files), 4)
        self.assertEqual(len(png_files), 4)

    def test_seeded_png_payloads_round_trip_and_validate(self) -> None:
        seed_fixture_directory(self.output_dir)

        for png_path in sorted(self.output_dir.glob("*_v3.png")):
            extracted = self.metadata_engine.extract_card_data(png_path.read_bytes())
            canonical = extract_trope_engine_card(extracted)
            result = self.validator.validate_card_json(canonical)
            self.assertTrue(result.success, png_path.name)
            self.assertEqual(extracted["spec"], "chara_card_v3")
            self.assertIn("name", extracted)
            self.assertIn(
                extracted["extensions"]["trope_engine"]["engine_type"],
                {"Meet-Cute", "Meet-Ugly", "Meet-Crazy", "Forced-Proximity"},
            )


if __name__ == "__main__":
    unittest.main()
