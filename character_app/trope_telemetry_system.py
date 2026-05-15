from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import logging
import os
from pathlib import Path
import platform
import queue
import subprocess
import threading
import time
from typing import Any, Callable

from .telemetry_filter import TelemetryFilteringMask

logger = logging.getLogger(__name__)

AchievementPayload = dict[str, str]
NotificationCallback = Callable[[str, str], None]


class TropeTelemetrySystem:
    def __init__(
        self,
        websocket_server_url: str | None = None,
        *,
        notification_callback: NotificationCallback | None = None,
        enable_native_popups: bool | None = None,
        retry_delay_seconds: float = 5.0,
        filtering_mask: TelemetryFilteringMask | None = None,
    ) -> None:
        self.server_url = websocket_server_url
        self.unlocked_achievements: set[str] = set()
        self.retry_delay_seconds = max(0.5, float(retry_delay_seconds))
        self.filtering_mask = filtering_mask or TelemetryFilteringMask()
        self._notification_callback = notification_callback
        self._enable_native_popups = (
            self._default_popup_state()
            if enable_native_popups is None
            else bool(enable_native_popups)
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._message_queue: asyncio.Queue[dict[str, Any] | None] | None = None
        self._loop_thread: threading.Thread | None = None
        self._loop_ready = threading.Event()
        self._stop_requested = threading.Event()
        self._startup_errors: queue.Queue[str] = queue.Queue()
        self.is_streaming = False

    def evaluate_live_achievements(
        self,
        state_card_dict: dict[str, Any],
    ) -> list[AchievementPayload]:
        new_unlocks: list[AchievementPayload] = []
        weights = state_card_dict.get("weights", {})
        phase = int(state_card_dict.get("current_phase", 1))
        lie_count = int(weights.get("lie_count", 0))

        achievement_definitions: dict[str, dict[str, Any]] = {
            "THE_BARRIER_CRACKS": {
                "condition": phase == 4,
                "title": "The Barrier Cracks",
                "desc": "Triggered a Phase 4 Climax or Breaking Point milestone route change.",
            },
            "FLAWLESS_TRUTH": {
                "condition": phase == 6 and lie_count == 0,
                "title": "The Flawless Truth",
                "desc": "Completed a true ending route without activating a pride-protection lie state.",
            },
            "PRESSURE_COOKER": {
                "condition": weights.get("confinement_stress", 0) == 5
                and max(
                    int(weights.get("proximity_awareness_acceleration", 0)),
                    int(weights.get("proximity_heat", 0)),
                )
                == 5,
                "title": "Pressure Cooker",
                "desc": "Maxed out both confinement stress and proximity awareness inside a forced-proximity route.",
            },
            "PRIDE_AND_PREJUDICE": {
                "condition": weights.get("rivalry_heat", 0) == 5
                and weights.get("angst_meter", 0) == 5,
                "title": "Pride and Prejudice",
                "desc": "Maxed out structural rivalry and narrative angst at the same time.",
            },
        }

        for achievement_id, item in achievement_definitions.items():
            if not item["condition"] or achievement_id in self.unlocked_achievements:
                continue
            self.unlocked_achievements.add(achievement_id)
            unlocked = {"id": achievement_id, "title": item["title"], "desc": item["desc"]}
            new_unlocks.append(unlocked)
            self._trigger_native_desktop_popup(item["title"], item["desc"])

        return new_unlocks

    def queue_telemetry_stream_packet(self, state_snapshot_dict: dict[str, Any]) -> bool:
        if not self.server_url or self._loop is None or self._message_queue is None:
            return False
        scrubbed_payload = self.filtering_mask.scrub_session_state(state_snapshot_dict)

        packet = {
            "timestamp": time.time(),
            "payload": scrubbed_payload,
            "total_achievements_unlocked": sorted(self.unlocked_achievements),
        }
        self._loop.call_soon_threadsafe(self._message_queue.put_nowait, packet)
        return True

    def start_background_dispatcher(self) -> bool:
        if not self.server_url:
            logger.info("Telemetry dispatcher idle: no WebSocket target configured.")
            return False
        if importlib.util.find_spec("websockets") is None:
            logger.warning("Telemetry dispatcher skipped: 'websockets' is not installed.")
            return False
        if self._loop_thread and self._loop_thread.is_alive():
            return True

        self._stop_requested.clear()
        self._loop_ready.clear()
        self._loop_thread = threading.Thread(
            target=self._run_dispatcher_thread,
            name="TropeTelemetryDispatcher",
            daemon=True,
        )
        self._loop_thread.start()
        self._loop_ready.wait(timeout=3.0)
        return not self._startup_errors.qsize()

    def stop_background_dispatcher(self) -> None:
        self._stop_requested.set()
        self.is_streaming = False
        loop = self._loop
        if loop is not None and self._message_queue is not None:
            loop.call_soon_threadsafe(self._message_queue.put_nowait, None)
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=3.0)
        self._loop_thread = None
        self._loop = None
        self._message_queue = None
        self._loop_ready.clear()

    def shutdown(self) -> None:
        self.stop_background_dispatcher()

    def _default_popup_state(self) -> bool:
        if platform.system() != "Darwin":
            return False
        return os.environ.get("QT_QPA_PLATFORM") != "offscreen"

    def _trigger_native_desktop_popup(self, title: str, description: str) -> None:
        logger.info("[ACHIEVEMENT UNLOCKED] %s - %s", title, description)
        if self._notification_callback is not None:
            self._notification_callback(title, description)
            return
        if not self._enable_native_popups:
            return

        applescript = (
            'display notification '
            f'{json.dumps(description)} '
            'with title '
            f'{json.dumps(title)} '
            'sound name "Glass"'
        )
        try:
            subprocess.run(
                ["osascript", "-e", applescript],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            logger.warning("Achievement popup dispatch failed: %s", exc)

    def _run_dispatcher_thread(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._message_queue = asyncio.Queue()
        self.is_streaming = True
        self._loop_ready.set()
        try:
            loop.run_until_complete(self._dispatcher_main())
        except Exception as exc:  # noqa: BLE001
            self._startup_errors.put(str(exc))
            logger.error("Telemetry dispatcher terminated unexpectedly: %s", exc)
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()

    async def _dispatcher_main(self) -> None:
        import websockets

        logger.info(
            "Asynchronous telemetry dispatcher connected to target: %s",
            self.server_url,
        )
        while not self._stop_requested.is_set():
            try:
                assert self.server_url is not None
                async with websockets.connect(self.server_url) as connection:
                    await self._stream_packets(connection)
            except (OSError, websockets.exceptions.ConnectionClosed) as exc:
                logger.warning(
                    "Telemetry WebSocket connection dropped: %s. Retrying in %.1fs.",
                    exc,
                    self.retry_delay_seconds,
                )
                await asyncio.sleep(self.retry_delay_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Fatal crash inside telemetry dispatcher loop: %s", exc)
                await asyncio.sleep(self.retry_delay_seconds)

    async def _stream_packets(self, connection: Any) -> None:
        assert self._message_queue is not None
        while not self._stop_requested.is_set():
            packet = await self._message_queue.get()
            try:
                if packet is None:
                    break
                await connection.send(json.dumps(packet, ensure_ascii=False))
            finally:
                self._message_queue.task_done()
