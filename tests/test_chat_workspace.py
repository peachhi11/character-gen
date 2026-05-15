from __future__ import annotations

import asyncio
import json
from pathlib import Path
import tempfile
import time
import unittest

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    httpx = None

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from character_app.chat_workspace import (
    ChatWorkspaceController,
    DesktopChatWorkspaceUI,
    build_chat_export_package,
    build_session_from_card_payload,
    generate_participant_turns_async,
    save_chat_export_package,
    simulate_participant_turns,
)
from character_app.config import ApiSettings, AppPaths


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


def _v3_card_payload(card_id: str, name: str, engine_type: str) -> dict:
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "id": card_id,
        "name": name,
        "description": f"{name} test card.",
        "first_mes": f"{name} opens the scene.",
        "extensions": {
            "trope_engine": {
                "engine_type": engine_type,
                "current_phase": 1,
                "weights": {
                    "platonic_trust": 2,
                    "romantic_awareness": 1,
                    "rivalry_heat": 2,
                    "repressed_desire": 1,
                    "angst_meter": 1,
                },
            }
        },
    }


class ChatWorkspaceControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.paths.ensure_directories()
        (self.paths.characters_dir / "maya.json").write_text(
            json.dumps(_v3_card_payload("maya_asset", "Maya Lin", "Meet-Cute")),
            encoding="utf-8",
        )
        (self.paths.characters_dir / "julian.json").write_text(
            json.dumps(_v3_card_payload("julian_asset", "Julian Vance", "Meet-Ugly")),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_session_from_card_payload_copies_engine_state(self) -> None:
        session = build_session_from_card_payload(
            "maya_asset",
            _v3_card_payload("maya_asset", "Maya Lin", "Meet-Cute"),
        )

        self.assertEqual(session.card_id, "maya_asset")
        self.assertEqual(session.engine_type, "Meet-Cute")
        self.assertEqual(session.weights["platonic_trust"], 2)
        self.assertEqual(session.weights["romantic_awareness"], 1)

    def test_controller_refreshes_library_and_sets_defaults(self) -> None:
        controller = ChatWorkspaceController(paths=self.paths)

        self.assertEqual(len(controller.participants), 2)
        self.assertEqual(controller.active_solo_character_id, "julian_asset")
        self.assertEqual(
            controller.active_group_participants,
            ["julian_asset", "maya_asset"],
        )

    def test_simulate_participant_turns_advances_weights_and_phase(self) -> None:
        controller = ChatWorkspaceController(paths=self.paths)
        controller.select_solo_character("maya_asset")
        snapshots = controller.participant_snapshots()

        for snapshot in snapshots:
            snapshot["session"]["weights"]["romantic_awareness"] = 3

        results = simulate_participant_turns(snapshots, "Stay with me.")

        self.assertEqual(len(results), 1)
        updated = results[0]["session"]
        self.assertEqual(updated["weights"]["romantic_awareness"], 4)
        self.assertEqual(updated["current_phase"], 4)
        self.assertIn("cracked-open", results[0]["message"]["content"])

    def test_simulate_participant_turns_supports_inverse_phase_trigger_rules(self) -> None:
        payload = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": "hero_asset",
            "name": "Dante Vale",
            "description": "A damaged protector.",
            "first_mes": "Stay back.",
            "extensions": {
                "trope_engine": {
                    "engine_type": "Tortured-Hero",
                    "current_phase": 1,
                    "weights": {
                        "internal_trauma": 5,
                        "emotional_detachment": 2,
                        "rescue_resistance": 3,
                        "angst_meter": 4,
                    },
                }
            },
        }
        session = build_session_from_card_payload("hero_asset", payload)
        snapshots = [
            {
                "participant_id": "hero_asset",
                "name": "Dante Vale",
                "engine_type": "Tortured-Hero",
                "session": session.to_dict(),
            }
        ]

        results = simulate_participant_turns(snapshots, "I'm not leaving.")

        self.assertEqual(results[0]["session"]["weights"]["emotional_detachment"], 1)
        self.assertEqual(results[0]["session"]["current_phase"], 4)

    def test_export_package_captures_backlog_and_participants(self) -> None:
        controller = ChatWorkspaceController(paths=self.paths)
        controller.queue_user_message("Hello.")
        controller.apply_turn_results(
            simulate_participant_turns(controller.participant_snapshots(), "Hello.")
        )

        export_package = build_chat_export_package(controller)

        self.assertEqual(export_package["spec"], "chara_card_v3_chat_history")
        self.assertEqual(export_package["spec_version"], "3.0")
        self.assertEqual(export_package["total_turns_compiled"], 2)
        self.assertEqual(len(export_package["participants_index"]), 1)

    def test_save_chat_export_package_writes_json_to_disk(self) -> None:
        controller = ChatWorkspaceController(paths=self.paths)
        controller.queue_user_message("Export this.")
        export_path = self.root / "chat_export.json"

        save_chat_export_package(controller.export_package(), export_path)

        saved = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["session_id"], controller.session_id)
        self.assertEqual(saved["history_buffer_stream"][0]["content"], "Export this.")


@unittest.skipIf(httpx is None, "httpx is not available in this Python environment")
class AsyncChatGenerationTest(unittest.TestCase):
    def _settings(self) -> ApiSettings:
        return ApiSettings(
            url="http://testserver/v1/chat/completions",
            model="gpt-4o-mini",
            key="test-key",
            max_tokens=128,
            temperature=0.7,
            top_p=0.95,
            timeout=10,
            max_retries=1,
            retry_delay=0,
        )

    def _client_factory(self) -> callable:
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content.decode("utf-8"))
            system_message = payload["messages"][0]["content"]
            if "Maya Lin" in system_message:
                return httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": "Maya replies live."}}]},
                )
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Julian replies live."}}]},
            )

        transport = httpx.MockTransport(handler)
        return lambda: httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        )

    def test_generate_participant_turns_async_uses_httpx_pipeline(self) -> None:
        snapshots = [
            {
                "participant_id": "maya_asset",
                "name": "Maya Lin",
                "engine_type": "Meet-Cute",
                "session": build_session_from_card_payload(
                    "maya_asset",
                    _v3_card_payload("maya_asset", "Maya Lin", "Meet-Cute"),
                ).to_dict(),
            },
            {
                "participant_id": "julian_asset",
                "name": "Julian Vance",
                "engine_type": "Meet-Ugly",
                "session": build_session_from_card_payload(
                    "julian_asset",
                    _v3_card_payload("julian_asset", "Julian Vance", "Meet-Ugly"),
                ).to_dict(),
            },
        ]

        async def run_test() -> list[dict]:
            return await generate_participant_turns_async(
                snapshots,
                user_message="Answer me.",
                message_history_snapshot=[{"sender": "user", "name": "PLAYER", "content": "Answer me."}],
                settings=self._settings(),
                client_factory=self._client_factory(),
            )

        results = asyncio.run(run_test())

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["message"]["content"], "Maya replies live.")
        self.assertEqual(results[1]["message"]["content"], "Julian replies live.")


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class DesktopChatWorkspaceUITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.paths.ensure_directories()
        (self.paths.characters_dir / "maya.json").write_text(
            json.dumps(_v3_card_payload("maya_asset", "Maya Lin", "Meet-Cute")),
            encoding="utf-8",
        )
        (self.paths.characters_dir / "julian.json").write_text(
            json.dumps(_v3_card_payload("julian_asset", "Julian Vance", "Meet-Ugly")),
            encoding="utf-8",
        )
        self.window = DesktopChatWorkspaceUI(paths=self.paths)

    def tearDown(self) -> None:
        if getattr(self.window, "turn_worker", None) is not None and self.window.turn_worker.isRunning():
            self.window.turn_worker.wait(2000)
        self.window.deleteLater()
        self.temp_dir.cleanup()

    def test_solo_mode_message_submission_renders_player_and_character_turn(self) -> None:
        self.window.msg_input_field.setText("Hello there.")
        self.window.execute_message_submission_flow()
        self._wait_for(lambda: len(self.window.controller.message_backlog) >= 2)

        html = self.window.chat_display_viewport.toHtml()
        self.assertIn("PLAYER", html)
        self.assertTrue(
            "Julian Vance" in html or "Maya Lin" in html,
            "Expected a character reply to be rendered into the chat viewport.",
        )
        self.assertTrue(
            "Meet-Ugly" in self.window.metrics_readout_pane.toPlainText()
            or "Meet-Cute" in self.window.metrics_readout_pane.toPlainText()
        )

    def test_group_mode_interleaves_selected_characters(self) -> None:
        self.window.view_selector.setCurrentText("Multi-Card Group Chat Arena")
        QApplication.processEvents()

        self.window.msg_input_field.setText("Both of you, focus.")
        self.window.execute_message_submission_flow()
        self._wait_for(lambda: len(self.window.controller.message_backlog) >= 3)

        html = self.window.chat_display_viewport.toHtml()
        self.assertIn("Maya Lin", html)
        self.assertIn("Julian Vance", html)
        self.assertIn(
            "Active Participants Token List",
            self.window.metrics_readout_pane.toPlainText(),
        )

    def test_export_flow_without_backlog_shows_status_warning(self) -> None:
        self.window.execute_json_file_compilation_export_flow()
        self.assertIn("Export cancelled", self.window.pipeline_status_label.text())

    def _wait_for(self, predicate, timeout_ms: int = 4000) -> None:
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            QApplication.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self.fail("Timed out waiting for the chat workspace to process the turn.")
