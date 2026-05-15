from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from PIL import Image

from character_app.drag_drop_listener import (
    LiveDragDropWorkspaceDemo,
    TropeDragDropListenerPanel,
    parse_card_asset_file,
)
from character_app.png_metadata_engine import PNGMetadataEngine


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


class DragDropListenerParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.png_metadata_engine = PNGMetadataEngine()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parse_card_asset_file_reads_json_payload(self) -> None:
        payload = {
            "spec": "chara_card_v3",
            "name": "Maya Lin",
            "extensions": {"trope_engine": {"engine_type": "Meet-Cute"}},
        }
        path = self.root / "maya.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        parsed = parse_card_asset_file(path)

        self.assertEqual(parsed["name"], "Maya Lin")
        self.assertEqual(
            parsed["extensions"]["trope_engine"]["engine_type"],
            "Meet-Cute",
        )

    def test_parse_card_asset_file_reads_png_metadata_payload(self) -> None:
        payload = {
            "spec": "chara_card_v2",
            "data": {
                "name": "Julian Vance",
                "extensions": {"trope_engine": {"engine_type": "Meet-Ugly"}},
            },
        }
        image = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        png_bytes = self.png_metadata_engine.inject_card_data(buffer.getvalue(), payload)
        path = self.root / "julian.png"
        path.write_bytes(png_bytes)

        parsed = parse_card_asset_file(path)

        self.assertEqual(parsed["data"]["name"], "Julian Vance")
        self.assertEqual(
            parsed["data"]["extensions"]["trope_engine"]["engine_type"],
            "Meet-Ugly",
        )

    def test_parse_card_asset_file_rejects_unsupported_suffix(self) -> None:
        path = self.root / "notes.txt"
        path.write_text("hello", encoding="utf-8")

        with self.assertRaises(ValueError):
            parse_card_asset_file(path)


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class DragDropListenerWidgetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.panel = TropeDragDropListenerPanel()
        self.window = LiveDragDropWorkspaceDemo()

    def tearDown(self) -> None:
        self.panel.deleteLater()
        self.window.deleteLater()
        self.temp_dir.cleanup()

    def test_panel_emits_payload_for_json_drop_pipeline(self) -> None:
        payload = {
            "spec": "chara_card_v3",
            "name": "Roxie Wilder",
            "extensions": {"trope_engine": {"engine_type": "Meet-Crazy"}},
        }
        path = self.root / "roxie.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        captured: list[tuple[dict, str]] = []
        self.panel.payload_extracted_signal.connect(
            lambda data, file_path: captured.append((data, file_path))
        )

        self.panel._execute_file_payload_extraction_pipeline(str(path))

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0]["name"], "Roxie Wilder")
        self.assertEqual(captured[0][1], str(path))

    def test_panel_shows_error_dialog_for_bad_json(self) -> None:
        path = self.root / "broken.json"
        path.write_text("{ not valid json", encoding="utf-8")

        with patch(
            "character_app.drag_drop_listener.QMessageBox.exec",
            return_value=0,
        ) as mocked_exec:
            self.panel._execute_file_payload_extraction_pipeline(str(path))

        mocked_exec.assert_called_once()

    def test_demo_maps_payload_into_labels(self) -> None:
        payload = {
            "spec": "chara_card_v3",
            "name": "Maya Lin",
            "extensions": {"trope_engine": {"engine_type": "Fake-Dating"}},
        }

        self.window.handle_incoming_extracted_payload_snapshot(
            payload,
            str(self.root / "maya.json"),
        )

        self.assertIn("CCV3", self.window.lbl_spec_type.text())
        self.assertIn("Maya Lin", self.window.lbl_name_field.text())
        self.assertIn("Fake-Dating", self.window.lbl_engine_field.text())
