from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

from .config import AppPaths
from .runtime_state import EngineStateCard, TropeStorageController


REQUIRED_STATE_KEYS = (
    "session_id",
    "card_id",
    "engine_type",
    "current_phase",
    "weights",
    "chat_history",
)


class StateIOController:
    def __init__(
        self,
        storage_controller: TropeStorageController,
        paths: AppPaths,
        base_save_dir: str | Path | None = None,
    ) -> None:
        self.storage_controller = storage_controller
        self.paths = paths
        self.save_dir = (
            Path(base_save_dir) if base_save_dir is not None else paths.runtime_saves_dir
        )
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def compile_and_save_to_disk(
        self,
        state_data: EngineStateCard | dict[str, Any],
        target_filepath: str | Path | None = None,
    ) -> Path:
        payload = self._normalize_state_payload(state_data)
        payload["last_updated"] = time.time()

        if target_filepath is None:
            session_id = str(payload.get("session_id", "unknown_session")).strip() or "unknown_session"
            target_path = self.save_dir / f"{session_id}.json"
        else:
            target_path = Path(target_filepath)
            if target_path.suffix.lower() != ".json":
                target_path = target_path.with_suffix(".json")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_controller.recovery_engine.safe_write_session(target_path, payload)
        return target_path

    def read_and_validate_from_disk(self, target_filepath: str | Path) -> dict[str, Any]:
        target_path = Path(target_filepath)
        backup_path = target_path.with_suffix(f"{target_path.suffix}.bak")
        if not target_path.exists() and not backup_path.exists():
            raise FileNotFoundError(
                f"Target save profile path '{target_path}' does not exist on disk."
            )

        payload = self.storage_controller.recovery_engine.safe_read_session(
            target_path,
            fallback_session_id=target_path.stem,
        )
        self._validate_payload_shape(payload)
        return payload

    def hydrate_state_card_from_disk(
        self, target_filepath: str | Path
    ) -> EngineStateCard:
        return EngineStateCard.from_dict(self.read_and_validate_from_disk(target_filepath))

    def _normalize_state_payload(
        self,
        state_data: EngineStateCard | dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(state_data, EngineStateCard):
            payload = state_data.to_dict()
        else:
            payload = json.loads(json.dumps(state_data))
        self._validate_payload_shape(payload)
        return payload

    def _validate_payload_shape(self, payload: dict[str, Any]) -> None:
        for key in REQUIRED_STATE_KEYS:
            if key not in payload:
                raise KeyError(
                    f"Corrupted file payload pattern: Missing critical state parameter field '{key}'."
                )

        if not isinstance(payload.get("weights"), dict):
            raise TypeError("Corrupted file payload pattern: 'weights' must be an object.")
        if not isinstance(payload.get("chat_history"), list):
            raise TypeError("Corrupted file payload pattern: 'chat_history' must be an array.")
