from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import time
from typing import Any


logger = logging.getLogger(__name__)


class DefensiveStorageRecoveryEngine:
    def __init__(self, max_retries: int = 3, initial_delay: float = 0.1) -> None:
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    def safe_write_session(
        self,
        target_filepath: str | Path,
        state_payload_dict: dict[str, Any],
    ) -> bool:
        target_path = Path(target_filepath)
        temp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
        backup_path = target_path.with_suffix(f"{target_path.suffix}.bak")
        retries = 0
        current_delay = self.initial_delay

        while retries < self.max_retries:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with temp_path.open("w", encoding="utf-8") as handle:
                    json.dump(state_payload_dict, handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    # Flush JSON contents to disk before promotion.
                    os.fsync(handle.fileno())

                if target_path.exists():
                    target_path.replace(backup_path)

                temp_path.replace(target_path)
                self._emergency_cleanup([temp_path])
                return True
            except (OSError, PermissionError) as disk_error:
                retries += 1
                logger.warning(
                    "Runtime save write collision on attempt %s/%s for %s: %s",
                    retries,
                    self.max_retries,
                    target_path,
                    disk_error,
                )
                self._emergency_cleanup([temp_path])
                if retries >= self.max_retries:
                    break
                time.sleep(current_delay)
                current_delay *= 2
            except Exception:
                self._emergency_cleanup([temp_path])
                logger.exception(
                    "Unhandled runtime save failure while writing %s", target_path
                )
                raise

        raise IOError(
            f"Failed to securely write runtime state after {self.max_retries} attempts."
        )

    def safe_read_session(
        self,
        target_filepath: str | Path,
        *,
        fallback_session_id: str | None = None,
    ) -> dict[str, Any]:
        target_path = Path(target_filepath)
        backup_path = target_path.with_suffix(f"{target_path.suffix}.bak")

        if target_path.exists():
            try:
                return self._read_json(target_path)
            except (json.JSONDecodeError, UnicodeDecodeError) as parse_error:
                logger.error(
                    "Primary runtime save is corrupted at %s: %s",
                    target_path,
                    parse_error,
                )

        if backup_path.exists():
            try:
                recovered_data = self._read_json(backup_path)
                backup_path.replace(target_path)
                logger.warning(
                    "Recovered runtime save from backup %s and restored %s",
                    backup_path,
                    target_path,
                )
                return recovered_data
            except Exception as backup_error:
                logger.critical(
                    "Backup runtime save is also unreadable for %s: %s",
                    target_path,
                    backup_error,
                )

        logger.critical(
            "Runtime save and backup are both unreadable for %s; generating salvage payload",
            target_path,
        )
        return self._generate_emergency_salvage_payload(
            session_id=fallback_session_id
        )

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise json.JSONDecodeError("Runtime save payload must be an object", "", 0)
        return data

    def _emergency_cleanup(self, paths: list[Path]) -> None:
        for path in paths:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                logger.debug("Unable to remove temporary runtime file %s", path)

    def _generate_emergency_salvage_payload(
        self,
        *,
        session_id: str | None = None,
        card_id: str = "UNKNOWN_SALVAGED_ASSET",
        engine_type: str = "Meet-Cute",
    ) -> dict[str, Any]:
        return {
            "session_id": session_id or "RECOVERED_FALLBACK_SESS",
            "card_id": card_id,
            "engine_type": engine_type,
            "current_phase": 1,
            "last_updated": time.time(),
            "weights": {
                "platonic_trust": 1,
                "romantic_awareness": 0,
                "rivalry_heat": 0,
                "repressed_desire": 0,
                "chaotic_chemistry": 0,
                "adrenaline_level": 0,
                "emotional_depth": 1,
                "confinement_stress": 0,
                "hostile_friction_heat": 0,
                "proximity_awareness_acceleration": 0,
                "proximity_heat": 0,
                "fear_of_loss": 1,
                "angst_meter": 0,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            },
            "chat_history": [
                {
                    "role": "system",
                    "content": "[SYSTEM INTEGRITY WARNING]: Session recovered via emergency fallback paths due to severe file system corruption.",
                }
            ],
        }
