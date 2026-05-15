from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from character_app.config import AppPaths
from character_app.runtime_state import EngineStateCard, TropeStorageController
from character_app.state_io_controller import StateIOController


class StateIOControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.paths.ensure_directories()
        self.storage_controller = TropeStorageController(self.paths)
        self.io_controller = StateIOController(self.storage_controller, self.paths)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_compile_and_save_to_disk_writes_runtime_snapshot(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        state.weights["rivalry_heat"] = 4

        saved = self.io_controller.compile_and_save_to_disk(state)

        self.assertEqual(saved.parent, self.paths.runtime_saves_dir)
        self.assertTrue(saved.exists())

    def test_compile_and_save_to_disk_honors_explicit_target_path(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        external_dir = self.root / "player_saves"

        saved = self.io_controller.compile_and_save_to_disk(
            state,
            external_dir / "custom_snapshot.json",
        )

        self.assertEqual(saved, external_dir / "custom_snapshot.json")
        self.assertTrue(saved.exists())

    def test_read_and_validate_from_disk_hydrates_saved_session(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        state.chat_history.append({"role": "user", "content": "You took my files."})
        target = self.io_controller.compile_and_save_to_disk(state)

        payload = self.io_controller.read_and_validate_from_disk(target)

        self.assertEqual(payload["session_id"], state.session_id)
        self.assertEqual(len(payload["chat_history"]), 1)

    def test_read_and_validate_from_disk_recovers_from_backup(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        state.weights["rivalry_heat"] = 2
        target = self.io_controller.compile_and_save_to_disk(state)

        state.weights["rivalry_heat"] = 4
        self.io_controller.compile_and_save_to_disk(state, target)
        target.write_text("{ broken", encoding="utf-8")

        payload = self.io_controller.read_and_validate_from_disk(target)

        self.assertEqual(payload["weights"]["rivalry_heat"], 2)

    def test_read_and_validate_from_disk_rejects_missing_required_keys(self) -> None:
        broken = self.root / "player_saves" / "broken.json"
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text('{"session_id": "sess_test"}', encoding="utf-8")

        with self.assertRaises(KeyError) as error:
            self.io_controller.read_and_validate_from_disk(broken)

        self.assertIn("Missing critical state parameter field", str(error.exception))


if __name__ == "__main__":
    unittest.main()
