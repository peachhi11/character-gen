from __future__ import annotations

from copy import deepcopy
import queue
import threading
from typing import Any

from .runtime_state import EngineStateCard, TropeStorageController


class TropeAutosaveDaemon:
    def __init__(
        self,
        storage_controller: TropeStorageController,
        interval_turns: int = 5,
    ) -> None:
        self.storage_controller = storage_controller
        self.interval_turns = max(1, int(interval_turns))
        self._pending_saves: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._turn_counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="TropeAutosaveDaemon",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def track_and_evaluate_message(self, session: EngineStateCard) -> None:
        with self._lock:
            turns = self._turn_counts.get(session.session_id, 0) + 1
            if turns >= self.interval_turns:
                self._turn_counts[session.session_id] = 0
                self._enqueue_session(session)
            else:
                self._turn_counts[session.session_id] = turns

    def force_immediate_save(self, session: EngineStateCard) -> None:
        with self._lock:
            self._turn_counts[session.session_id] = 0
        self._enqueue_session(session)

    def _enqueue_session(self, session: EngineStateCard) -> None:
        snapshot = deepcopy(session.to_dict())
        self._pending_saves.put(snapshot)

    def _run(self) -> None:
        while not self._stop_event.is_set() or not self._pending_saves.empty():
            try:
                snapshot = self._pending_saves.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self.storage_controller.save_session_state(
                    EngineStateCard.from_dict(snapshot)
                )
            finally:
                self._pending_saves.task_done()
