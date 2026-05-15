from __future__ import annotations

import asyncio
import unittest

try:
    import httpx
    from character_app.cache_sync_manager import CacheSyncManagerWorker
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    httpx = None
    CacheSyncManagerWorker = None
    QApplication = None


APP = QApplication.instance() or QApplication([]) if QApplication is not None else None


@unittest.skipIf(
    CacheSyncManagerWorker is None or httpx is None,
    "PyQt6 and httpx are not available in this Python environment",
)
class CacheSyncManagerWorkerTest(unittest.TestCase):
    def _make_client_factory(self, pool_token: str) -> callable:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/pool/status":
                return httpx.Response(
                    200,
                    json={
                        "status": "SUCCESS",
                        "active_sessions": {"sess_1234abcd": pool_token},
                    },
                )
            if request.url.path == "/api/session/sess_1234abcd":
                return httpx.Response(
                    200,
                    json={
                        "status": "SUCCESS",
                        "session_id": "sess_1234abcd",
                        "card_id": "maya_asset",
                        "engine_type": "Meet-Cute",
                        "current_phase": 2,
                        "last_updated": 1715691720.0,
                        "updated_weights": {
                            "platonic_trust": 4,
                            "romantic_awareness": 1,
                            "angst_meter": 1,
                            "lie_active": False,
                            "lie_count": 0,
                            "distance_locked": False,
                        },
                        "chat_history": [],
                    },
                )
            return httpx.Response(404, json={"detail": "not found"})

        transport = httpx.MockTransport(handler)
        return lambda: httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        )

    def test_poll_once_emits_remote_patch_when_sync_token_changes(self) -> None:
        worker = CacheSyncManagerWorker(
            backend_api_url="http://testserver",
            client_factory=self._make_client_factory("etag_v1"),
        )
        captured: list[tuple[dict, str]] = []
        worker.sync_success_signal.connect(
            lambda payload, session_id: captured.append((payload, session_id))
        )

        async def run_test() -> None:
            async with worker._client_factory() as client:
                await worker._poll_once(client)

        asyncio.run(run_test())

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][1], "sess_1234abcd")
        self.assertEqual(captured[0][0]["card_id"], "maya_asset")
        self.assertEqual(worker.active_sessions_etag["sess_1234abcd"], "etag_v1")

    def test_poll_once_skips_duplicate_sync_token(self) -> None:
        worker = CacheSyncManagerWorker(
            backend_api_url="http://testserver",
            client_factory=self._make_client_factory("etag_v1"),
        )
        captured: list[tuple[dict, str]] = []
        worker.sync_success_signal.connect(
            lambda payload, session_id: captured.append((payload, session_id))
        )

        async def run_test() -> None:
            async with worker._client_factory() as client:
                await worker._poll_once(client)
                await worker._poll_once(client)

        asyncio.run(run_test())

        self.assertEqual(len(captured), 1)


if __name__ == "__main__":
    unittest.main()
