from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import tempfile
import time
import unittest

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from PIL import Image

from character_app.card_library import CharacterCardLibrary
from character_app.config import AppPaths
from character_app.png_metadata_engine import PNGMetadataEngine

if QApplication is not None:
    from character_app.card_library import DesktopLibraryBrowserUI


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


class CharacterCardLibraryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.paths.ensure_directories()
        self.library = CharacterCardLibrary(paths=self.paths)
        self.png_metadata_engine = PNGMetadataEngine()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_v3_json(self) -> Path:
        payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "maya_v3_asset",
            "name": "Maya Lin",
            "description": "A sharp-tongued rival with a soft center.",
            "extensions": {
                "trope_engine": {
                    "engine_type": "Meet-Ugly",
                }
            },
        }
        path = self.paths.characters_dir / "maya_v3_asset.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _write_v2_png(self) -> Path:
        payload = {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": "Julian Vance",
                "description": "A polished academic rival.",
                "extensions": {
                    "trope_engine": {
                        "engine_type": "Second-Chance",
                    }
                },
            },
        }
        image = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = self.png_metadata_engine.inject_card_data(buffer.getvalue(), payload)
        path = self.paths.characters_dir / "julian_vance.png"
        path.write_bytes(encoded)
        return path

    def _write_runtime_state(self) -> Path:
        payload = {
            "session_id": "sess_abc12345",
            "card_id": "maya_v3_asset",
            "engine_type": "Matchmaker-Crush",
            "current_phase": 2,
            "last_updated": 1715691720.0,
            "weights": {
                "performative_guidance": 4,
                "proxy_resentment": 2,
                "internal_frictional_heat": 1,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": False,
            },
            "chat_history": [],
        }
        path = self.paths.runtime_saves_dir / "sess_abc12345.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_scan_and_rebuild_library_index_catalogs_character_and_runtime_records(self) -> None:
        self._write_v3_json()
        self._write_v2_png()
        self._write_runtime_state()

        total = self.library.scan_and_rebuild_library_index()

        self.assertEqual(total, 3)
        self.assertIn("maya_v3_asset", self.library.card_index)
        self.assertIn("sess_abc12345", self.library.card_index)
        self.assertEqual(
            self.library.card_index["maya_v3_asset"]["spec_format"],
            "CCV3",
        )
        self.assertEqual(
            self.library.card_index["sess_abc12345"]["record_type"],
            "runtime_state",
        )

    def test_get_card_payload_for_deployment_loads_json_card(self) -> None:
        self._write_v3_json()
        self.library.scan_and_rebuild_library_index()

        payload = self.library.get_card_payload_for_deployment("maya_v3_asset")

        self.assertEqual(payload["name"], "Maya Lin")
        self.assertEqual(payload["extensions"]["trope_engine"]["engine_type"], "Meet-Ugly")

    def test_get_card_payload_for_deployment_loads_png_card(self) -> None:
        self._write_v2_png()
        self.library.scan_and_rebuild_library_index()

        records = self.library.list_records()
        self.assertEqual(len(records), 1)
        payload = self.library.get_card_payload_for_deployment(records[0]["id"])

        self.assertEqual(payload["data"]["name"], "Julian Vance")
        self.assertEqual(
            payload["data"]["extensions"]["trope_engine"]["engine_type"],
            "Second-Chance",
        )

    def test_get_card_payload_for_deployment_loads_runtime_state(self) -> None:
        self._write_runtime_state()
        self.library.scan_and_rebuild_library_index()

        payload = self.library.get_card_payload_for_deployment("sess_abc12345")

        self.assertEqual(payload["engine_type"], "Matchmaker-Crush")
        self.assertEqual(payload["card_id"], "maya_v3_asset")


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class DesktopLibraryBrowserUITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.paths.ensure_directories()
        image = Image.new("RGBA", (24, 24), (45, 128, 210, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "bea_asset",
            "name": "Bea",
            "description": "A test character.",
            "assets": [{"uri": f"data:image/png;base64,{encoded_image}"}],
            "extensions": {
                "trope_engine": {
                    "engine_type": "Fake-Dating",
                }
            },
        }
        (self.paths.characters_dir / "bea_asset.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )
        self.window = DesktopLibraryBrowserUI(paths=self.paths)

    def tearDown(self) -> None:
        self.window.deleteLater()
        self.temp_dir.cleanup()

    def test_refresh_populates_table_rows(self) -> None:
        self.window.trigger_refresh_library_index_pass()

        self.assertEqual(self.window.library_table.rowCount(), 1)
        self.assertIn("1 assets found", self.window.lbl_summary.text())

    def test_search_filter_reduces_visible_rows_immediately(self) -> None:
        extra_payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "maya_asset",
            "name": "Maya",
            "description": "Another test character.",
            "extensions": {
                "trope_engine": {
                    "engine_type": "Meet-Ugly",
                }
            },
        }
        (self.paths.characters_dir / "maya_asset.json").write_text(
            json.dumps(extra_payload),
            encoding="utf-8",
        )

        self.window.trigger_refresh_library_index_pass()
        self.assertEqual(self.window.library_table.rowCount(), 2)

        self.window.search_bar_input.setText("bea")
        QApplication.processEvents()

        self.assertEqual(self.window.library_table.rowCount(), 1)
        self.assertEqual(self.window.library_table.item(0, 0).text(), "Bea")

    def test_thumbnail_decoder_renders_selected_sprite(self) -> None:
        self.window.trigger_refresh_library_index_pass()
        self.window.library_table.setCurrentCell(0, 0)

        deadline = time.time() + 2.0
        while time.time() < deadline:
            QApplication.processEvents()
            pixmap = self.window.sprite_manager.image_canvas.pixmap()
            if pixmap is not None and not pixmap.isNull():
                break
            time.sleep(0.01)

        pixmap = self.window.sprite_manager.image_canvas.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())


if __name__ == "__main__":
    unittest.main()
