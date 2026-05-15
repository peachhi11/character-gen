from __future__ import annotations

import asyncio
import json
import socket
import unittest

try:
    import websockets
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    websockets = None

from character_app.telemetry_filter import TelemetryFilteringMask
from character_app.trope_telemetry_system import TropeTelemetrySystem


class _ImmediateLoop:
    def call_soon_threadsafe(self, callback, *args) -> None:
        callback(*args)


class _ImmediateQueue:
    def __init__(self) -> None:
        self.items: list[object] = []

    def put_nowait(self, item: object) -> None:
        self.items.append(item)


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TropeTelemetrySystemTest(unittest.TestCase):
    def test_evaluate_live_achievements_unlocks_once(self) -> None:
        notifications: list[tuple[str, str]] = []
        system = TropeTelemetrySystem(
            notification_callback=lambda title, desc: notifications.append((title, desc)),
            enable_native_popups=False,
        )
        payload = {
            "current_phase": 4,
            "weights": {
                "lie_count": 0,
                "confinement_stress": 0,
                "proximity_awareness_acceleration": 0,
                "rivalry_heat": 0,
                "angst_meter": 1,
            },
        }

        first = system.evaluate_live_achievements(payload)
        second = system.evaluate_live_achievements(payload)

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["id"], "THE_BARRIER_CRACKS")
        self.assertEqual(second, [])
        self.assertEqual(len(notifications), 1)

    def test_queue_telemetry_stream_packet_deep_copies_payload(self) -> None:
        system = TropeTelemetrySystem("ws://localhost:8765/dev/console")
        system._loop = _ImmediateLoop()  # type: ignore[assignment]
        system._message_queue = _ImmediateQueue()  # type: ignore[assignment]
        source = {
            "current_phase": 3,
            "weights": {"private_confusion": 2, "lie_count": 1},
            "chat_history": [{"role": "user", "content": "hi"}],
        }

        queued = system.queue_telemetry_stream_packet(source)
        source["weights"]["private_confusion"] = 5
        source["chat_history"].append({"role": "character", "content": "later"})

        self.assertTrue(queued)
        self.assertEqual(len(system._message_queue.items), 1)  # type: ignore[union-attr]
        packet = system._message_queue.items[0]  # type: ignore[union-attr]
        self.assertEqual(packet["payload"]["weights"]["private_confusion"], 2)
        self.assertEqual(len(packet["payload"]["chat_history"]), 1)
        self.assertIn("[REDACTED_CONTENT_LEN_", packet["payload"]["chat_history"][0]["content"])

    def test_queue_telemetry_stream_packet_returns_false_without_target(self) -> None:
        system = TropeTelemetrySystem()
        self.assertFalse(system.queue_telemetry_stream_packet({"weights": {}}))

    def test_privacy_scrub_regression(self) -> None:
        filter_mask = TelemetryFilteringMask(
            redact_chat_history=True,
            anonymous_mode=True,
        )
        raw_session = {
            "user_id": "secret_account_token",
            "session_id": "sess_user_9921_alpha_run",
            "chat_history": [
                {
                    "role": "user",
                    "content": "High security personal text payload.",
                }
            ],
        }

        scrubbed_output = filter_mask.scrub_session_state(raw_session)

        self.assertNotEqual(scrubbed_output["user_id"], "secret_account_token")
        self.assertNotEqual(scrubbed_output["session_id"], "sess_user_9921_alpha_run")
        self.assertIn(
            "[REDACTED_CONTENT_LEN_",
            scrubbed_output["chat_history"][0]["content"],
        )

    def test_websocket_dispatch_sends_scrubbed_payload(self) -> None:
        if websockets is None:
            self.skipTest("websockets is not available in this Python environment")
        asyncio.run(self._run_websocket_dispatch_test())

    async def _run_websocket_dispatch_test(self) -> None:
        captured_messages: list[dict] = []
        message_received = asyncio.Event()
        port = _find_free_port()

        async def handler(websocket) -> None:
            async for message in websocket:
                captured_messages.append(json.loads(message))
                message_received.set()

        server = await websockets.serve(handler, "127.0.0.1", port)
        system = TropeTelemetrySystem(
            f"ws://127.0.0.1:{port}",
            enable_native_popups=False,
        )

        try:
            self.assertTrue(system.start_background_dispatcher())
            queued = system.queue_telemetry_stream_packet(
                {
                    "session_id": "sess_user_9921_alpha_run",
                    "user_id": "account_id_julian_vance_player",
                    "current_phase": 4,
                    "weights": {"rivalry_heat": 4, "repressed_desire": 3},
                    "chat_history": [
                        {
                            "role": "user",
                            "content": "I step closer, leaning directly over your desk workspace layout.",
                        },
                        {
                            "role": "character",
                            "content": "Julian freezes completely, their breath catching as they stare.",
                        },
                    ],
                }
            )
            self.assertTrue(queued)

            await asyncio.wait_for(message_received.wait(), timeout=3.0)
            self.assertEqual(len(captured_messages), 1)
            packet = captured_messages[0]
            payload = packet["payload"]
            self.assertTrue(payload["session_id"].startswith("sess_"))
            self.assertIn("***", payload["session_id"])
            self.assertTrue(payload["user_id"].startswith("anon_"))
            for turn in payload["chat_history"]:
                self.assertIn("[REDACTED_CONTENT_LEN_", turn["content"])
            self.assertEqual(payload["weights"]["rivalry_heat"], 4)
        finally:
            system.shutdown()
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    unittest.main()
