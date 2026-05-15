from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest
import zipfile

try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QApplication = None

from character_app.config import AppPaths
from character_app.db_sweep_pipeline import (
    DatabaseSweepPipelineUI,
    archive_stale_session_files,
    collect_runtime_session_paths,
)
from character_app.runtime_state import EngineStateCard, TropeStorageController


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


class DatabaseSweepPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.paths.ensure_directories()
        self.storage_controller = TropeStorageController(paths=self.paths)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_named_session(self, file_name: str, *, age_days: int) -> Path:
        path = self.paths.runtime_saves_dir / file_name
        payload = {
            "session_id": path.stem,
            "card_id": "maya_v3_asset",
            "engine_type": "Fake-Dating",
            "current_phase": 2,
            "last_updated": time.time(),
            "weights": {"private_confusion": 2},
            "chat_history": [],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        stale_time = time.time() - (age_days * 86400)
        path.touch()
        import os

        os.utime(path, (stale_time, stale_time))
        return path

    def test_collect_runtime_session_paths_supports_repo_and_legacy_patterns(self) -> None:
        sess_path = self._write_named_session("sess_livecase.json", age_days=1)
        state_path = self._write_named_session("state_legacycase.json", age_days=1)
        (self.paths.runtime_saves_dir / "notes.json").write_text("{}", encoding="utf-8")

        collected = collect_runtime_session_paths(self.paths.runtime_saves_dir)

        self.assertEqual(collected, sorted([sess_path, state_path]))

    def test_archive_stale_session_files_zips_old_session_and_keeps_fresh_one(self) -> None:
        stale_path = self._write_named_session("sess_stale001.json", age_days=9)
        fresh_path = self._write_named_session("sess_fresh001.json", age_days=1)

        report = archive_stale_session_files(
            self.paths.runtime_saves_dir,
            max_age_days=7,
        )

        self.assertEqual(report.status, "SUCCESS")
        self.assertEqual(report.archived_files, [stale_path.name])
        self.assertIn(fresh_path.name, report.skipped_files)
        self.assertFalse(stale_path.exists())
        self.assertTrue(fresh_path.exists())
        self.assertIsNotNone(report.archive_package)

        archive_path = Path(report.archive_package or "")
        self.assertTrue(archive_path.exists())
        with zipfile.ZipFile(archive_path, "r") as archive_handle:
            self.assertEqual(archive_handle.namelist(), [stale_path.name])

    def test_archive_stale_session_files_skips_live_active_session_ids(self) -> None:
        session = EngineStateCard(card_id="vance_v3_asset", engine_type="Meet-Ugly")
        file_path = self.storage_controller.save_session_state(session)
        stale_time = time.time() - (9 * 86400)
        import os

        os.utime(file_path, (stale_time, stale_time))

        report = archive_stale_session_files(
            self.paths.runtime_saves_dir,
            max_age_days=7,
            active_session_ids={session.session_id},
        )

        self.assertEqual(report.archived_records, 0)
        self.assertIn(Path(file_path).name, report.skipped_files)
        self.assertTrue(Path(file_path).exists())


@unittest.skipIf(QApplication is None, "PyQt6 is not available in this Python environment")
class DatabaseSweepPipelineUITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = AppPaths(root=self.root)
        self.paths.ensure_directories()
        self.window = DatabaseSweepPipelineUI(paths=self.paths)

    def tearDown(self) -> None:
        if getattr(self.window, "worker", None) is not None and self.window.worker.isRunning():
            self.window.worker.is_cancelled = True
            self.window.worker.wait(2000)
        self.window.deleteLater()
        self.temp_dir.cleanup()

    def test_ui_worker_archives_stale_session_offscreen(self) -> None:
        target = self.paths.runtime_saves_dir / "sess_ui_stale.json"
        target.write_text(
            json.dumps(
                {
                    "session_id": "sess_ui_stale",
                    "card_id": "maya_v3_asset",
                    "engine_type": "Second-Chance",
                    "current_phase": 1,
                    "last_updated": time.time(),
                    "weights": {},
                    "chat_history": [],
                }
            ),
            encoding="utf-8",
        )
        stale_time = time.time() - (10 * 86400)
        import os

        os.utime(target, (stale_time, stale_time))

        self.window.spin_age.setValue(7)
        self.window.toggle_sweep_pipeline_execution()
        self._wait_for(lambda: self.window.worker is not None and not self.window.worker.isRunning())

        archive_dir = self.paths.runtime_saves_dir / "archives"
        self.assertFalse(target.exists())
        self.assertTrue(list(archive_dir.glob("archive_batch_*.zip")))
        self.assertIn("CONCLUDED SUCCESSFULLY", self.window.log_terminal.toPlainText())

    def _wait_for(self, predicate, timeout_ms: int = 4000) -> None:
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            QApplication.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self.fail("Timed out waiting for the sweep worker to complete.")
