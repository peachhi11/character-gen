from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import time
import uuid
from typing import Any

from .config import AppPaths
from .defensive_storage import DefensiveStorageRecoveryEngine
from .trope_engine_catalog import all_runtime_weight_keys


BOOLEAN_WEIGHT_KEYS = frozenset({"lie_active", "distance_locked", "safeword_breached"})
UNBOUNDED_INT_WEIGHT_KEYS = frozenset({"lie_count"})
DEFAULT_RUNTIME_WEIGHTS: dict[str, int | bool] = {
    key: (False if key in BOOLEAN_WEIGHT_KEYS else 0)
    for key in all_runtime_weight_keys()
}


def _new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:8]}"


@dataclass
class EngineStateCard:
    card_id: str
    engine_type: str
    session_id: str = field(default_factory=_new_session_id)
    current_phase: int = 1
    last_updated: float = field(default_factory=time.time)
    weights: dict[str, int | bool] = field(
        default_factory=lambda: dict(DEFAULT_RUNTIME_WEIGHTS)
    )
    chat_history: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "card_id": self.card_id,
            "engine_type": self.engine_type,
            "current_phase": self.current_phase,
            "last_updated": self.last_updated,
            "weights": dict(self.weights),
            "chat_history": list(self.chat_history),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EngineStateCard":
        instance = cls(
            card_id=data["card_id"],
            engine_type=data["engine_type"],
            session_id=data.get("session_id", _new_session_id()),
        )
        instance.current_phase = int(data.get("current_phase", 1))
        instance.last_updated = float(data.get("last_updated", time.time()))
        instance.weights = dict(DEFAULT_RUNTIME_WEIGHTS)
        instance.weights.update(data.get("weights", {}))
        for key in BOOLEAN_WEIGHT_KEYS:
            instance.weights[key] = bool(instance.weights.get(key, False))
        instance.chat_history = list(data.get("chat_history", []))
        return instance


class TropeStorageController:
    def __init__(
        self,
        paths: AppPaths | None = None,
        storage_directory: Path | str | None = None,
    ) -> None:
        self.paths = paths or AppPaths()
        if storage_directory is None:
            self.storage_directory = self.paths.runtime_saves_dir
        else:
            self.storage_directory = Path(storage_directory)
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        self.recovery_engine = DefensiveStorageRecoveryEngine()

    def session_path(self, session_id: str) -> Path:
        return self.storage_directory / f"{session_id}.json"

    def list_session_ids(self) -> list[str]:
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        return sorted(path.stem for path in self.storage_directory.glob("*.json"))

    def save_session_state(self, state_card: EngineStateCard) -> Path:
        state_card.last_updated = time.time()
        file_path = self.session_path(state_card.session_id)
        self.recovery_engine.safe_write_session(file_path, state_card.to_dict())
        return file_path

    def load_session_state(self, session_id: str) -> EngineStateCard:
        file_path = self.session_path(session_id)
        backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
        if not file_path.exists() and not backup_path.exists():
            raise FileNotFoundError(
                f"Requested save instance '{session_id}' not found."
            )

        data = self.recovery_engine.safe_read_session(
            file_path, fallback_session_id=session_id
        )
        return EngineStateCard.from_dict(data)

    def modify_metric_weight(
        self, state_card: EngineStateCard, key: str, value: Any
    ) -> EngineStateCard:
        if key not in state_card.weights:
            raise KeyError(
                f"Target metric key '{key}' is not an applicable trope engine parameter modifier."
            )

        current_value = state_card.weights[key]
        if key in BOOLEAN_WEIGHT_KEYS:
            if not isinstance(value, bool):
                raise TypeError(
                    f"Value modifier for key '{key}' must resolve to boolean format types."
                )
            state_card.weights[key] = value
        else:
            try:
                int_value = int(value)
            except (ValueError, TypeError) as exc:
                raise TypeError(
                    f"Value modifier for metric key '{key}' must cast to numerical integer formats."
                ) from exc

            if key in UNBOUNDED_INT_WEIGHT_KEYS:
                state_card.weights[key] = max(0, int_value)
            else:
                state_card.weights[key] = max(0, min(5, int_value))

        if state_card.weights[key] != current_value:
            state_card.last_updated = time.time()
        return state_card

    def append_chat_message(
        self, state_card: EngineStateCard, role: str, content: str
    ) -> EngineStateCard:
        state_card.chat_history.append({"role": role, "content": content})
        state_card.last_updated = time.time()
        return state_card

    def update_phase(
        self, state_card: EngineStateCard, current_phase: int
    ) -> EngineStateCard:
        state_card.current_phase = max(1, min(6, int(current_phase)))
        state_card.last_updated = time.time()
        return state_card
