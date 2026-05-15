from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    httpx = None

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    QThread = None
    pyqtSignal = None


logger = logging.getLogger(__name__)


def _looks_like_session_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    required = {"session_id", "card_id", "engine_type", "current_phase", "updated_weights", "chat_history"}
    return required.issubset(payload.keys())


def _normalize_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": payload["session_id"],
        "card_id": payload["card_id"],
        "engine_type": payload["engine_type"],
        "current_phase": payload["current_phase"],
        "last_updated": payload.get("last_updated", 0.0),
        "weights": dict(payload.get("updated_weights", {})),
        "chat_history": list(payload.get("chat_history", [])),
    }


if QThread is not None and pyqtSignal is not None and httpx is not None:
    class CacheSyncManagerWorker(QThread):
        sync_success_signal = pyqtSignal(dict, str)
        network_fault_signal = pyqtSignal(str)

        def __init__(
            self,
            backend_api_url: str,
            sync_interval_seconds: float = 5.0,
            *,
            client_factory: Callable[[], httpx.AsyncClient] | None = None,
            parent=None,
        ) -> None:
            super().__init__(parent)
            self.api_url = backend_api_url.rstrip("/")
            self.interval = max(0.5, float(sync_interval_seconds))
            self.is_monitoring = False
            self.active_sessions_etag: dict[str, str] = {}
            self._client_factory = client_factory or (lambda: httpx.AsyncClient())

        def start_sync_daemon(self) -> None:
            if not self.api_url:
                return
            self.is_monitoring = True
            if not self.isRunning():
                self.start()

        def stop_sync_daemon(self) -> None:
            self.is_monitoring = False
            if self.isRunning():
                self.wait(5000)

        def run(self) -> None:  # type: ignore[override]
            asyncio.run(self._network_polling_lifecycle())

        async def _network_polling_lifecycle(self) -> None:
            logger.info(
                "Asynchronous Sync Hook deployed to endpoint tracking target: %s",
                self.api_url,
            )
            async with self._client_factory() as client:
                while self.is_monitoring:
                    await self._poll_once(client)
                    await asyncio.sleep(self.interval)

        async def _poll_once(self, client: httpx.AsyncClient) -> None:
            try:
                response = await client.get(f"{self.api_url}/api/pool/status", timeout=2.0)
                if response.status_code != 200:
                    self.network_fault_signal.emit(
                        f"Sync Intercept: Remote pool status returned HTTP {response.status_code}."
                    )
                    return

                pool_summary = response.json()
                if not isinstance(pool_summary, dict):
                    self.network_fault_signal.emit(
                        "Critical Sync Failure: Remote pool status payload is not a JSON object."
                    )
                    return

                await self._evaluate_cache_deltas(client, pool_summary)
            except httpx.RequestError as exc:
                self.network_fault_signal.emit(
                    f"Sync Intercept: Network unreachable, retrying... ({exc})"
                )
            except Exception as exc:  # noqa: BLE001
                self.network_fault_signal.emit(f"Critical Sync Failure: {exc}")

        async def _evaluate_cache_deltas(
            self,
            client: httpx.AsyncClient,
            pool_summary: dict[str, Any],
        ) -> None:
            remote_sessions = pool_summary.get("active_sessions", {})
            if not isinstance(remote_sessions, dict):
                self.network_fault_signal.emit(
                    "Critical Sync Failure: Remote pool summary is missing a valid 'active_sessions' map."
                )
                return

            remote_ids = {str(session_id) for session_id in remote_sessions}
            for stale_id in list(self.active_sessions_etag):
                if stale_id not in remote_ids:
                    self.active_sessions_etag.pop(stale_id, None)

            for session_id_raw, last_modified_hash_raw in remote_sessions.items():
                session_id = str(session_id_raw)
                last_modified_hash = str(last_modified_hash_raw)
                known_etag = self.active_sessions_etag.get(session_id, "")
                if last_modified_hash == known_etag:
                    continue

                try:
                    session_response = await client.get(
                        f"{self.api_url}/api/session/{session_id}",
                        timeout=2.0,
                    )
                    if session_response.status_code != 200:
                        continue

                    payload = session_response.json()
                    if not _looks_like_session_payload(payload):
                        self.network_fault_signal.emit(
                            f"Critical Sync Failure: Session '{session_id}' payload failed shape validation."
                        )
                        continue

                    self.active_sessions_etag[session_id] = last_modified_hash
                    self.sync_success_signal.emit(
                        _normalize_session_payload(payload),
                        session_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to cleanly integrate data patch for session '%s': %s",
                        session_id,
                        exc,
                    )
else:
    class CacheSyncManagerWorker:  # pragma: no cover - PyQt-only shim
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError(
                "PyQt6 and httpx are required to use CacheSyncManagerWorker."
            )
