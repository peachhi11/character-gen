from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from character_app.png_metadata_engine import PNGMetadataEngine
from character_app.repo_asset_parser import (
    RepoAssetInventoryParser,
    run_mac_batch_parser_app,
    run_repo_asset_parser_app,
)


class RepoAssetInventoryParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo_dir = self.root / "repo"
        self.output_dir = self.root / "ledger"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.parser = RepoAssetInventoryParser()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_scan_directory_builds_inventory_ledger_for_mixed_assets(self) -> None:
        (self.repo_dir / "v3_card.json").write_text(
            json.dumps(
                {
                    "spec": "chara_card_v3",
                    "spec_version": "3.0",
                    "id": "maya_v3",
                    "name": "Maya",
                    "extensions": {"trope_engine": {"engine_type": "Meet-Cute"}},
                }
            ),
            encoding="utf-8",
        )
        (self.repo_dir / "v2_card.json").write_text(
            json.dumps(
                {
                    "spec": "chara_card_v2",
                    "spec_version": "2.0",
                    "data": {
                        "name": "Julian",
                        "description": "Academic rival.",
                        "extensions": {"trope_engine": {"engine_type": "Meet-Ugly"}},
                    },
                }
            ),
            encoding="utf-8",
        )
        (self.repo_dir / "v1_card.json").write_text(
            json.dumps(
                {
                    "name": "Roxie",
                    "description": "Wild card route.",
                }
            ),
            encoding="utf-8",
        )
        (self.repo_dir / "lore.entries").write_text(
            json.dumps({"entries": {"1": {"content": "Archive basement lore"}}}),
            encoding="utf-8",
        )
        (self.repo_dir / "broken.json").write_text("{ bad json", encoding="utf-8")
        self._write_png_card(self.repo_dir / "embedded.png")

        report = self.parser.scan_directory(self.repo_dir, self.output_dir)

        self.assertEqual(report["status"], "SUCCESS")
        self.assertEqual(report["v3_count"], 2)
        self.assertEqual(report["v2_count"], 1)
        self.assertEqual(report["v1_count"], 1)
        self.assertEqual(report["wb_count"], 1)
        self.assertEqual(report["fail_count"], 1)

        ledger_path = self.output_dir / "repo_asset_inventory_ledger.json"
        self.assertTrue(ledger_path.exists())
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(len(ledger["character_cards_v3"]), 2)
        png_entry = next(
            item for item in ledger["character_cards_v3"] if item["filename"] == "embedded.png"
        )
        self.assertTrue(png_entry["is_embedded_png_metadata"])

    def test_scan_directory_returns_empty_for_no_supported_assets(self) -> None:
        (self.repo_dir / "README.md").write_text("nothing here", encoding="utf-8")

        report = self.parser.scan_directory(self.repo_dir, self.output_dir)

        self.assertEqual(report["status"], "EMPTY")

    def test_batch_parser_compatibility_entrypoint_alias_matches_existing_launcher(self) -> None:
        self.assertIs(run_mac_batch_parser_app, run_repo_asset_parser_app)

    def _write_png_card(self, path: Path) -> None:
        image = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "embedded_v3",
            "name": "Embedded Avery",
            "extensions": {"trope_engine": {"engine_type": "Fake-Dating"}},
        }
        png_bytes = PNGMetadataEngine().inject_card_data(buffer.getvalue(), payload)
        path.write_bytes(png_bytes)


if __name__ == "__main__":
    unittest.main()
