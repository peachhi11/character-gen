from __future__ import annotations

import json
import os
from pathlib import Path
import time

from PyQt6.QtCore import QThread, pyqtSignal


class TelemetrySyncHook(QThread):
    state_mutated_signal = pyqtSignal(dict)
    access_error_signal = pyqtSignal(str)

    def __init__(
        self,
        target_filepath: str | Path | None = None,
        check_interval_seconds: float = 1.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.target_filepath = str(target_filepath) if target_filepath else ""
        self.interval = max(0.2, float(check_interval_seconds))
        self.is_monitoring = False
        self.last_known_modification_time = 0.0

    def set_target_filepath(self, target_filepath: str | Path | None) -> None:
        self.target_filepath = str(target_filepath) if target_filepath else ""
        self.last_known_modification_time = 0.0
        if self.target_filepath and os.path.exists(self.target_filepath):
            self.last_known_modification_time = os.path.getmtime(self.target_filepath)

    def start_monitoring(self) -> None:
        if not self.target_filepath:
            return
        if os.path.exists(self.target_filepath):
            self.last_known_modification_time = os.path.getmtime(self.target_filepath)
        self.is_monitoring = True
        if not self.isRunning():
            self.start()

    def stop_monitoring(self) -> None:
        self.is_monitoring = False
        if self.isRunning():
            self.wait()

    def run(self) -> None:  # type: ignore[override]
        while self.is_monitoring:
            if self.target_filepath and os.path.exists(self.target_filepath):
                try:
                    current_mtime = os.path.getmtime(self.target_filepath)
                    if current_mtime > self.last_known_modification_time:
                        self.last_known_modification_time = current_mtime
                        with open(self.target_filepath, "r", encoding="utf-8") as handle:
                            updated_payload = json.load(handle)
                        if isinstance(updated_payload, dict):
                            self.state_mutated_signal.emit(updated_payload)
                        else:
                            self.access_error_signal.emit(
                                "Telemetry Sync collision caught: payload is not a JSON object."
                            )
                except (json.JSONDecodeError, OSError) as file_lock_error:
                    self.access_error_signal.emit(
                        f"Telemetry Sync collision caught: {str(file_lock_error)}"
                    )
            time.sleep(self.interval)
