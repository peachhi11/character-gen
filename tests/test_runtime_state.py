from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest

from character_app.config import AppPaths
from character_app.defensive_storage import DefensiveStorageRecoveryEngine
from character_app.runtime_state import EngineStateCard, TropeStorageController


class RuntimeStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.controller = TropeStorageController(self.paths)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_engine_state_card_serializes_and_rehydrates(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        state.current_phase = 4
        state.weights["rivalry_heat"] = 4
        state.chat_history.append({"role": "user", "content": "You took my files."})

        hydrated = EngineStateCard.from_dict(state.to_dict())

        self.assertEqual(hydrated.card_id, "vance_v3_asset")
        self.assertEqual(hydrated.engine_type, "Meet-Ugly")
        self.assertEqual(hydrated.current_phase, 4)
        self.assertEqual(hydrated.weights["rivalry_heat"], 4)
        self.assertEqual(len(hydrated.chat_history), 1)

    def test_modify_metric_weight_clamps_numeric_metrics(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")

        self.controller.modify_metric_weight(state, "rivalry_heat", 9)
        self.controller.modify_metric_weight(state, "angst_meter", -3)
        self.controller.modify_metric_weight(state, "lie_count", 12)

        self.assertEqual(state.weights["rivalry_heat"], 5)
        self.assertEqual(state.weights["angst_meter"], 0)
        self.assertEqual(state.weights["lie_count"], 12)

    def test_modify_metric_weight_validates_boolean_metrics(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        self.controller.modify_metric_weight(state, "distance_locked", True)
        self.assertTrue(state.weights["distance_locked"])

        with self.assertRaises(TypeError):
            self.controller.modify_metric_weight(state, "distance_locked", "yes")

    def test_modify_metric_weight_rejects_unknown_keys(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        with self.assertRaises(KeyError):
            self.controller.modify_metric_weight(state, "unknown_metric", 1)

    def test_save_and_load_session_state_uses_runtime_saves_directory(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        self.controller.modify_metric_weight(state, "rivalry_heat", 4)
        self.controller.append_chat_message(
            state, "char", "Then work faster next time."
        )

        file_path = self.controller.save_session_state(state)
        reloaded = self.controller.load_session_state(state.session_id)

        self.assertEqual(file_path.parent, self.paths.runtime_saves_dir)
        self.assertEqual(reloaded.weights["rivalry_heat"], 4)
        self.assertEqual(len(reloaded.chat_history), 1)

    def test_append_chat_message_and_update_phase_refresh_timestamps(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        baseline = state.last_updated
        time.sleep(0.01)
        self.controller.append_chat_message(state, "user", "You took my workspace files.")
        after_chat = state.last_updated
        time.sleep(0.01)
        self.controller.update_phase(state, 8)

        self.assertGreater(after_chat, baseline)
        self.assertGreater(state.last_updated, after_chat)
        self.assertEqual(state.current_phase, 6)
        self.assertEqual(len(state.chat_history), 1)

    def test_runtime_saves_do_not_touch_character_asset_directory(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        file_path = self.controller.save_session_state(state)

        self.assertTrue(file_path.exists())
        self.assertEqual(list(self.paths.characters_dir.glob("*.json")), [])

    def test_controller_accepts_storage_directory_only_constructor_form(self) -> None:
        storage_dir = self.root / "runtime_saves"
        controller = TropeStorageController(storage_directory=storage_dir)
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")

        controller.modify_metric_weight(state, "rivalry_heat", 4)
        controller.modify_metric_weight(state, "distance_locked", True)
        state.chat_history.append(
            {"role": "user", "content": "You took my workspace files."}
        )
        state.chat_history.append(
            {"role": "char", "content": "Then work faster next time."}
        )

        file_path = controller.save_session_state(state)
        reloaded = controller.load_session_state(state.session_id)

        self.assertEqual(file_path.parent, storage_dir)
        self.assertEqual(reloaded.weights["rivalry_heat"], 4)
        self.assertTrue(reloaded.weights["distance_locked"])
        self.assertEqual(len(reloaded.chat_history), 2)

    def test_safe_write_rotates_previous_save_to_backup(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        self.controller.modify_metric_weight(state, "rivalry_heat", 2)
        file_path = self.controller.save_session_state(state)

        self.controller.modify_metric_weight(state, "rivalry_heat", 4)
        self.controller.save_session_state(state)

        backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
        self.assertTrue(backup_path.exists())
        with backup_path.open("r", encoding="utf-8") as handle:
            backup_data = json.load(handle)
        self.assertEqual(backup_data["weights"]["rivalry_heat"], 2)

    def test_load_session_state_restores_from_backup_when_primary_is_corrupt(self) -> None:
        state = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        self.controller.modify_metric_weight(state, "rivalry_heat", 2)
        file_path = self.controller.save_session_state(state)
        self.controller.modify_metric_weight(state, "rivalry_heat", 4)
        self.controller.save_session_state(state)

        with file_path.open("w", encoding="utf-8") as handle:
            handle.write("{ not valid json")

        restored = self.controller.load_session_state(state.session_id)

        self.assertEqual(restored.weights["rivalry_heat"], 2)
        with file_path.open("r", encoding="utf-8") as handle:
            restored_payload = json.load(handle)
        self.assertEqual(restored_payload["weights"]["rivalry_heat"], 2)

    def test_safe_read_returns_salvage_payload_when_primary_and_backup_are_corrupt(self) -> None:
        file_path = self.paths.runtime_saves_dir / "broken_session.json"
        backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
        file_path.write_text("{ broken", encoding="utf-8")
        backup_path.write_text("{ also broken", encoding="utf-8")

        recovered = self.controller.recovery_engine.safe_read_session(
            file_path, fallback_session_id="broken_session"
        )

        self.assertEqual(recovered["session_id"], "broken_session")
        self.assertEqual(recovered["card_id"], "UNKNOWN_SALVAGED_ASSET")
        self.assertEqual(recovered["weights"]["platonic_trust"], 1)
        self.assertEqual(recovered["chat_history"][0]["role"], "system")


class DefensiveStorageRecoveryEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.engine = DefensiveStorageRecoveryEngine(initial_delay=0.0)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_safe_write_and_read_round_trip(self) -> None:
        file_path = self.root / "session.json"
        payload = {"session_id": "sess_alpha", "weights": {"rivalry_heat": 4}}

        self.assertTrue(self.engine.safe_write_session(file_path, payload))
        restored = self.engine.safe_read_session(file_path)

        self.assertEqual(restored, payload)


if __name__ == "__main__":
    unittest.main()
