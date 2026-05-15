from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from character_app.config import AppPaths
from character_app.runtime_state import EngineStateCard, TropeStorageController

if QApplication is not None:
    from character_app.ui import CHARACTER_THEME, SessionStateWorkspaceTab


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


class _TelemetryStub:
    def __init__(self) -> None:
        self.queued_payloads: list[dict] = []

    def evaluate_live_achievements(self, state_payload: dict) -> list[dict[str, str]]:
        if state_payload.get("current_phase") == 4:
            return [
                {
                    "id": "THE_BARRIER_CRACKS",
                    "title": "The Barrier Cracks",
                    "desc": "Triggered a Phase 4 Climax or Breaking Point milestone route change.",
                }
            ]
        return []

    def queue_telemetry_stream_packet(self, state_payload: dict) -> bool:
        self.queued_payloads.append(state_payload)
        return True

    def shutdown(self) -> None:
        return None


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class SessionStateWorkspaceTabTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.paths = AppPaths(root=Path(self.temp_dir.name))
        self.paths.ensure_directories()
        self.storage_controller = TropeStorageController(self.paths)
        self.tab = SessionStateWorkspaceTab(
            paths=self.paths,
            storage_controller=self.storage_controller,
            theme=CHARACTER_THEME,
        )

    def tearDown(self) -> None:
        self.tab.shutdown()
        self.tab.deleteLater()
        self.temp_dir.cleanup()

    def test_refresh_session_list_reads_runtime_saves_directory(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        self.storage_controller.save_session_state(session)

        self.tab.refresh_session_list()

        self.assertIn(session.session_id, [self.tab.session_combo.itemText(i) for i in range(self.tab.session_combo.count())])

    def test_execute_mock_message_injection_updates_chat_history_and_json(self) -> None:
        self.tab.inject_role_combo.setCurrentText("user")
        self.tab.input_inject_msg.setText("You took my workspace files.")

        self.tab.execute_mock_message_injection()

        self.assertEqual(len(self.tab.state_card.chat_history), 2)
        self.assertIn("PLAYER:", self.tab.chat_viewport.toPlainText())
        self.assertIn('"chat_history"', self.tab.json_terminal.toPlainText())

    def test_save_state_to_disk_uses_file_dialog_and_controller(self) -> None:
        target = self.paths.runtime_saves_dir / "ui_saved_session.json"

        with patch(
            "character_app.ui.QFileDialog.getSaveFileName",
            return_value=(str(target), "JSON Files (*.json)"),
        ):
            self.tab.save_state_to_disk()

        self.assertTrue(target.exists())
        self.assertEqual(self.tab.current_session_path, target)

    def test_load_state_from_disk_uses_controller_validation(self) -> None:
        session = EngineStateCard(card_id="maya_asset", engine_type="Meet-Cute")
        session.weights["platonic_trust"] = 4
        target = self.paths.runtime_saves_dir / "ui_load_session.json"
        self.storage_controller.recovery_engine.safe_write_session(target, session.to_dict())

        with patch(
            "character_app.ui.QFileDialog.getOpenFileName",
            return_value=(str(target), "JSON Files (*.json)"),
        ):
            self.tab.load_state_from_disk()

        self.assertEqual(self.tab.state_card.card_id, "maya_asset")
        self.assertEqual(self.tab.state_card.weights["platonic_trust"], 4)

    def test_set_selected_engine_updates_bucket_browser(self) -> None:
        self.tab.set_selected_engine("Babysitter")

        self.assertEqual(self.tab.combo_bucket.currentData(), "WORKPLACE")
        self.assertEqual(
            self.tab.combo_subgroup.currentData(),
            "Services (Domestic)",
        )
        self.assertEqual(self.tab.combo_engine.currentData(), "Babysitter")
        self.assertEqual(self.tab.state_card.engine_type, "Babysitter")

    def test_refresh_sprite_preview_loads_linked_png_card(self) -> None:
        image = Image.new("RGBA", (24, 24), (220, 90, 120, 255))
        image_path = self.paths.characters_dir / "maya_asset.png"
        image.save(image_path, format="PNG")

        self.tab.input_card_id.setText("maya_asset")
        self.tab.refresh_sprite_preview_from_linked_card()

        self.assertIsNotNone(self.tab.sprite_manager.image_canvas.pixmap())

    def test_sync_ui_to_model_state_runs_telemetry_pipeline(self) -> None:
        stub = _TelemetryStub()
        self.tab.telemetry_system.shutdown()
        self.tab.telemetry_system = stub
        self.tab.combo_phase.setCurrentIndex(3)

        self.tab.sync_ui_to_model_state()

        self.assertGreaterEqual(len(stub.queued_payloads), 1)
        self.assertEqual(stub.queued_payloads[-1]["current_phase"], 4)
        self.assertIn("Achievement unlocked", self.tab.status_label.text())

    def test_handle_asynchronous_cache_hydration_patch_reloads_current_session(self) -> None:
        session = EngineStateCard(card_id="maya_asset", engine_type="Meet-Cute")
        session.weights["platonic_trust"] = 4
        self.tab.state_card = session
        self.tab.hydrate_ui_from_save_state()

        updated_payload = session.to_dict()
        updated_payload["current_phase"] = 4
        updated_payload["weights"]["platonic_trust"] = 5

        self.tab.handle_asynchronous_cache_hydration_patch(
            updated_payload,
            session.session_id,
        )

        self.assertEqual(self.tab.state_card.current_phase, 4)
        self.assertEqual(self.tab.state_card.weights["platonic_trust"], 5)
        self.assertIn("Cache synchronized", self.tab.status_label.text())

    def test_trigger_external_catalyst_plot_twist_flow_updates_engine_and_directive(self) -> None:
        session = EngineStateCard(
            card_id="vance_v3_asset",
            engine_type="Fake-Relationship",
        )
        session.weights.update(
            {
                "performative_closeness": 5,
                "private_confusion": 4,
                "boundary_panic_heat": 4,
                "angst_meter": 2,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": False,
            }
        )
        self.tab.state_card = session
        self.tab.hydrate_ui_from_save_state()

        self.tab.trigger_external_catalyst_plot_twist_flow("Runaway-Fiance")

        self.assertEqual(self.tab.state_card.engine_type, "Runaway-Fiance")
        self.assertEqual(self.tab.state_card.current_phase, 5)
        self.assertFalse(self.tab.state_card.weights["lie_active"])
        self.assertIn("INSTINCTIVE FLIGHT", self.tab.directive_terminal.toPlainText())
        self.assertIn("Plot twist executed", self.tab.status_label.text())
