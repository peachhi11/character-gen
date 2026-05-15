from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

import websockets

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from character_app.telemetry_filter import TelemetryFilteringMask


class TelemetryTestHarnessServer:
    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.server = None
        self.captured_payloads: list[dict[str, Any]] = []

    async def start(self) -> None:
        self.server = await websockets.serve(self.handler, self.host, self.port)
        print(
            f"[TEST HARNESS]: Mock Server successfully mounted on ws://{self.host}:{self.port}"
        )

    async def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            print("[TEST HARNESS]: Mock Server safely terminated and ports freed.")

    async def handler(self, websocket) -> None:
        try:
            async for message in websocket:
                packet = json.loads(message)
                self.captured_payloads.append(packet)
                print(
                    f"[TEST HARNESS RECEIVED]: Captured tracking packet block at {packet.get('timestamp')}"
                )
                self._assert_payload_compliance(packet)
        except websockets.exceptions.ConnectionClosed:
            return

    def _assert_payload_compliance(self, packet: dict[str, Any]) -> None:
        payload = packet.get("payload", {})
        chat_log = payload.get("chat_history", [])

        print("  -> Running assertions matching security validation criteria...")
        for turn in chat_log:
            assert "[REDACTED_CONTENT_LEN_" in turn["content"], (
                "Security Regression: Plaintext chat leaks detected inside network pipeline: "
                f"{turn['content']}"
            )

        assert "weights" in payload, (
            "Structural Error: Packet data payload is missing 'weights' metadata objects."
        )
        assert 0 <= payload["weights"].get("rivalry_heat", 0) <= 5, (
            "Value Error: Metric parameters broke 0-5 clamp bounds."
        )

        print(
            "  -> [ASSERTION SUCCESS]: Packet fully complies with telemetry data contract constraints."
        )


async def execute_integration_test_lifecycle() -> None:
    harness = TelemetryTestHarnessServer()
    await harness.start()

    privacy_mask = TelemetryFilteringMask(
        redact_chat_history=True,
        anonymous_mode=True,
    )

    live_gameplay_state = {
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

    cleansed_packet = privacy_mask.scrub_session_state(live_gameplay_state)

    try:
        async with websockets.connect("ws://localhost:8765") as client:
            packed_envelope = {
                "timestamp": 1715691720.0,
                "payload": cleansed_packet,
            }
            await client.send(json.dumps(packed_envelope))
            await asyncio.sleep(0.1)
    finally:
        await harness.stop()


if __name__ == "__main__":
    asyncio.run(execute_integration_test_lifecycle())
