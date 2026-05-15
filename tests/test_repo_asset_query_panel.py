from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from character_app.repo_asset_query_panel import (
    RepoAssetLedgerStore,
    purge_filepaths,
    run_mac_query_dashboard_app,
    run_repo_asset_query_panel_app,
)

if QApplication is not None:
    from character_app.repo_asset_query_panel import TropeQueryInterfacePanel


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


class RepoAssetLedgerStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.ledger_path = self.root / "repo_asset_inventory_ledger.json"
        self.ledger_path.write_text(
            json.dumps(
                {
                    "character_cards_v3": [
                        {
                            "character_name": "Julian Vance",
                            "file_path": "/tmp/julian.json",
                            "filename": "julian.json",
                        }
                    ],
                    "character_cards_v2_legacy": [],
                    "character_cards_v1_legacy": [],
                    "worldbooks_parsed": [
                        {
                            "source_filename": "lore.entries",
                            "file_path": "/tmp/lore.entries",
                        }
                    ],
                    "unmapped_or_corrupted_assets": [
                        {
                            "file_path": "/tmp/broken.json",
                            "error": "bad json",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.store = RepoAssetLedgerStore()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_and_filter_ledger_records(self) -> None:
        self.store.load_from_path(self.ledger_path)

        matches = self.store.iter_filtered_records("julian", {"V3_CARD", "CORRUPTED"})

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], "V3_CARD")
        self.assertEqual(matches[0][1]["filename"], "julian.json")

    def test_remove_item_updates_internal_cache(self) -> None:
        self.store.load_from_path(self.ledger_path)

        self.store.remove_item("CORRUPTED", "/tmp/broken.json")

        self.assertEqual(self.store.corrupted_filepaths(), [])

    def test_load_from_path_accepts_alternate_corrupted_key_name(self) -> None:
        alternate_path = self.root / "alternate_ledger.json"
        alternate_path.write_text(
            json.dumps(
                {
                    "character_cards_v3": [],
                    "character_cards_v2_legacy": [],
                    "character_cards_v1_legacy": [],
                    "worldbooks_parsed": [],
                    "corrupted_or_unmapped_assets": [
                        {
                            "file_path": "/tmp/broken_alt.json",
                            "error": "bad json alt",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        self.store.load_from_path(alternate_path)

        self.assertEqual(self.store.corrupted_filepaths(), ["/tmp/broken_alt.json"])

    def test_purge_filepaths_removes_files_from_disk(self) -> None:
        target = self.root / "corrupted.json"
        target.write_text("{ broken", encoding="utf-8")

        report = purge_filepaths([str(target)])

        self.assertEqual(report["success_count"], 1)
        self.assertFalse(target.exists())

    def test_query_dashboard_compatibility_entrypoint_alias_matches_existing_launcher(self) -> None:
        self.assertIs(run_mac_query_dashboard_app, run_repo_asset_query_panel_app)


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class TropeQueryInterfacePanelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.panel = TropeQueryInterfacePanel()
        self.panel.store.ledger_data = {
            "character_cards_v3": [],
            "character_cards_v2_legacy": [],
            "character_cards_v1_legacy": [],
            "worldbooks_parsed": [],
            "unmapped_or_corrupted_assets": [
                {
                    "file_path": "/tmp/broken.json",
                    "error": "bad json",
                }
            ],
        }

    def tearDown(self) -> None:
        self.panel.deleteLater()

    def test_row_selection_enables_purge_button(self) -> None:
        self.panel.refresh_query_results_viewport()
        self.panel.results_list_widget.setCurrentRow(0)

        self.assertTrue(self.panel.btn_purge_asset.isEnabled())
        self.assertIn("CORRUPTED", self.panel.asset_details_viewer.toPlainText())


if __name__ == "__main__":
    unittest.main()
