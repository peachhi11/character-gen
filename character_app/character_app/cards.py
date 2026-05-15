from __future__ import annotations

import base64
import copy
from datetime import datetime
import json
from io import BytesIO
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from .card_schema_validation import CharacterCardValidator
from .config import AppPaths, load_template_payload
from .defensive_storage import DefensiveStorageRecoveryEngine
from .models import CharacterCard


class CharacterRepository:
    def __init__(self, paths: AppPaths, directory: Path | None = None):
        self.paths = paths
        self.directory = directory or self.paths.characters_dir
        self.schema_validator = CharacterCardValidator()
        self.recovery_engine = DefensiveStorageRecoveryEngine()
        self.paths.ensure_directories()

    def list_names(self) -> list[str]:
        names: set[str] = set()
        self.directory.mkdir(parents=True, exist_ok=True)
        for file_path in self.directory.iterdir():
            if file_path.suffix.lower() == ".json":
                names.add(file_path.stem)
            elif file_path.suffix.lower() == ".png":
                try:
                    with Image.open(file_path) as image:
                        if "chara" in image.info:
                            names.add(file_path.stem)
                except Exception:
                    continue
        return sorted(names)

    def load(self, identifier: str) -> CharacterCard:
        if Path(identifier).is_absolute():
            file_path = Path(identifier)
        else:
            base = self.directory / identifier
            file_path = base
            if not file_path.exists():
                if base.with_suffix(".json").exists():
                    file_path = base.with_suffix(".json")
                elif base.with_suffix(".png").exists():
                    file_path = base.with_suffix(".png")
                else:
                    raise RuntimeError(f"Character not found: {identifier}")

        if file_path.suffix.lower() == ".json":
            payload = self.load_json_payload(file_path)
            if self._is_engine_state_payload(payload):
                raise RuntimeError(
                    "Engine-state character cards passed schema validation but cannot yet "
                    "be opened in the standard chara-card editor."
                )
            return CharacterCard.from_payload(payload)

        with Image.open(file_path) as image:
            image.load()
            encoded = image.info.get("chara")
            if not encoded:
                raise RuntimeError(f"Character data not found in {file_path.name}")
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            if self._is_engine_state_payload(payload):
                self._validate_engine_state_payload(payload, file_path)
                raise RuntimeError(
                    "Engine-state character cards are JSON-only. PNG metadata embedding is reserved for standard chara-card payloads."
                )
            card = CharacterCard.from_payload(payload)
            card.image_data = image.copy()
            return card

    def save(self, card: CharacterCard, file_format: str = "json") -> Path:
        card.modified_at = datetime.now()
        save_name = card.name.strip() or "Unnamed"
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.directory / save_name
        payload = card.to_payload(copy.deepcopy(load_template_payload(self.paths)))

        if file_format == "json":
            return self.save_json_payload(payload, destination.with_suffix(".json"))

        file_path = destination.with_suffix(".png")
        image = card.image_data or Image.new("RGBA", (400, 600), (255, 255, 255, 0))
        metadata = PngInfo()
        metadata.add_text("chara", base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8"))
        output = BytesIO()
        image.save(output, format="PNG", pnginfo=metadata)
        file_path.write_bytes(output.getvalue())
        return file_path

    def load_json_payload(self, identifier: str | Path) -> dict:
        file_path = Path(identifier)
        payload = self._load_json_payload_with_recovery(file_path)
        if self._is_engine_state_payload(payload):
            return self._validate_engine_state_payload(payload, file_path)
        return payload

    def save_json_payload(self, payload: dict, identifier: str | Path) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / identifier
        if file_path.suffix.lower() != ".json":
            file_path = file_path.with_suffix(".json")

        output_payload = copy.deepcopy(payload)
        if self._is_engine_state_payload(output_payload):
            output_payload = self._validate_engine_state_payload(output_payload, file_path)

        self.recovery_engine.safe_write_session(file_path, output_payload)
        return file_path

    def _is_engine_state_payload(self, payload: object) -> bool:
        if not isinstance(payload, dict):
            return False
        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and (
            "engine_type" in metadata or "base_relationship" in metadata
        ):
            return True
        return any(
            key in payload
            for key in (
                "card_id",
                "trope_engine_weights",
                "dialogue_nodes",
                "meet_cute_origin",
                "meet_ugly_origin",
                "meet_crazy_origin",
                "forced_proximity_origin",
                "meet_context",
            )
        )

    def _validate_engine_state_payload(
        self, payload: dict, source: Path
    ) -> dict:
        result = self.schema_validator.validate_card_json(payload)
        if not result.success:
            detail = "; ".join(result.errors)
            raise RuntimeError(
                f"Engine-state card validation failed for {source.name}: {detail}"
            )
        return result.normalized_card or payload

    def _load_json_payload_with_recovery(self, file_path: Path) -> dict:
        backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")

        if file_path.exists():
            try:
                return self._read_json_object(file_path)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                if backup_path.exists():
                    try:
                        recovered = self._read_json_object(backup_path)
                        backup_path.replace(file_path)
                        return recovered
                    except (json.JSONDecodeError, UnicodeDecodeError) as backup_exc:
                        raise RuntimeError(
                            f"Character card payload is malformed in both {file_path.name} and its backup: {backup_exc}"
                        ) from backup_exc
                raise RuntimeError(
                    f"Character card payload is malformed and no recoverable backup exists for {file_path.name}: {exc}"
                ) from exc

        if backup_path.exists():
            try:
                recovered = self._read_json_object(backup_path)
                backup_path.replace(file_path)
                return recovered
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(
                    f"Character card backup is malformed for {file_path.name}: {exc}"
                ) from exc

        raise FileNotFoundError(file_path)

    def _read_json_object(self, file_path: Path) -> dict:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise json.JSONDecodeError("Character card payload must be an object", "", 0)
        return payload
