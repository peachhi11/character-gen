from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
from typing import Any
import uuid

from .mode_switcher import TropeModeSwitcher


logger = logging.getLogger(__name__)


class TropeDatabaseMigrationManager:
    def __init__(self, create_backups: bool = True) -> None:
        self.create_backups = create_backups
        self.processed_count = 0
        self.upgraded_count = 0
        self.failure_count = 0
        self.extracted_lore_nodes = 0
        self.mode_switcher = TropeModeSwitcher()

    def batch_migrate_directory(
        self,
        source_dir_path: str | Path,
        output_dir_path: str | Path | None = None,
        *,
        progress_callback=None,
        log_callback=None,
        cancel_check=None,
    ) -> dict[str, Any]:
        self.processed_count = 0
        self.upgraded_count = 0
        self.failure_count = 0
        self.extracted_lore_nodes = 0

        source_dir = Path(source_dir_path)
        if not source_dir.exists():
            raise FileNotFoundError(
                f"Source transformation target directory path '{source_dir}' does not exist."
            )

        target_output_dir = Path(output_dir_path) if output_dir_path else source_dir
        target_output_dir.mkdir(parents=True, exist_ok=True)

        self._emit_log(log_callback, f"Beginning batch migration cycle loop. Scanning: {source_dir}")

        targets = self.collect_targets(source_dir)
        total_files = len(targets)

        if total_files == 0:
            metrics_report = {
                "status": "EMPTY",
                "total_files_scanned": 0,
                "successful_upgrades": 0,
                "failed_parses": 0,
                "lore_nodes_compiled": 0,
            }
            self._emit_log(log_callback, "No valid character profiles or worldbook files discovered.")
            return metrics_report

        for index, source_file_path in enumerate(targets, start=1):
            if cancel_check and cancel_check():
                metrics_report = {
                    "status": "CANCELLED",
                    "total_files_scanned": self.processed_count,
                    "successful_upgrades": self.upgraded_count,
                    "failed_parses": self.failure_count,
                    "lore_nodes_compiled": self.extracted_lore_nodes,
                }
                self._emit_log(log_callback, "Processing sequence terminated by user request.")
                return metrics_report

            self.processed_count += 1
            relative_path = source_file_path.relative_to(source_dir)
            dest_file_path = target_output_dir / relative_path
            dest_file_path.parent.mkdir(parents=True, exist_ok=True)
            self._emit_log(
                log_callback,
                f"Ingesting file target [{index}/{total_files}]: {source_file_path.name}",
            )
            self._process_single_target(source_file_path, dest_file_path, target_output_dir, log_callback)
            if progress_callback is not None:
                progress_callback(int(index / total_files * 100))

        metrics_report = {
            "status": "COMPLETED",
            "total_files_scanned": self.processed_count,
            "successful_upgrades": self.upgraded_count,
            "failed_parses": self.failure_count,
            "lore_nodes_compiled": self.extracted_lore_nodes,
        }
        self._emit_log(log_callback, f"Migration processing lifecycle finalized: {metrics_report}")
        return metrics_report

    def collect_targets(self, source_dir: Path) -> list[Path]:
        return sorted(
            path
            for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".json", ".entries"}
        )

    def _process_single_target(
        self,
        src_path: Path,
        dest_path: Path,
        output_dir: Path,
        log_callback=None,
    ) -> None:
        try:
            if self._is_worldbook_target(src_path):
                nodes_found = self._extract_legacy_worldbook_entries(src_path, output_dir)
                self.extracted_lore_nodes += nodes_found
                self._emit_log(
                    log_callback,
                    f"  -> Extracted {nodes_found} structural worldbook tokens into memory caches.",
                )
                return

            with src_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            detected_type, normalized_payload = (
                self.mode_switcher.identify_and_normalize_payload(payload)
            )

            if detected_type == "CHARACTER_CARD_V2":
                if self.create_backups:
                    backup_path = src_path.with_suffix(f"{src_path.suffix}.bak")
                    shutil.copyfile(src_path, backup_path)

                upgraded_ccv3 = self._finalize_v3_payload(payload, normalized_payload)
                with dest_path.open("w", encoding="utf-8") as out_handle:
                    json.dump(upgraded_ccv3, out_handle, indent=2, ensure_ascii=False)
                self.upgraded_count += 1
                self._emit_log(
                    log_callback,
                    f"  -> Successfully upgraded legacy card asset frame: '{src_path}' -> '{dest_path}'",
                )
            elif src_path != dest_path:
                shutil.copyfile(src_path, dest_path)

        except Exception as exc:  # noqa: BLE001
            self.failure_count += 1
            self._emit_log(
                log_callback,
                f"  -> [PARSING CRASH ON PATH]: {src_path}: {exc}",
                error=True,
            )

    def _finalize_v3_payload(
        self, source_payload: dict[str, Any], normalized_payload: dict[str, Any]
    ) -> dict[str, Any]:
        v3_payload = json.loads(json.dumps(normalized_payload))
        trope_engine = (
            v3_payload.setdefault("extensions", {}).get("trope_engine") or {}
        )
        source_trope_engine = (
            source_payload.get("data", {})
            .get("extensions", {})
            .get("trope_engine")
        )
        heuristic_fallback = self._deduce_missing_trope_extensions(
            self._heuristic_text(source_payload)
        )

        if not isinstance(source_trope_engine, dict) or not source_trope_engine:
            v3_payload["extensions"]["trope_engine"] = heuristic_fallback
        elif not trope_engine.get("weights"):
            trope_engine["weights"] = heuristic_fallback["weights"]
            trope_engine.setdefault("engine_type", heuristic_fallback["engine_type"])
            trope_engine.setdefault("current_phase", 1)
            trope_engine.setdefault("origin_context", heuristic_fallback["origin_context"])
            trope_engine.setdefault("dialogue_nodes", heuristic_fallback["dialogue_nodes"])

        v3_payload["spec"] = "chara_card_v3"
        v3_payload["spec_version"] = "3.0"
        existing_tags = v3_payload.get("group_tags", [])
        if not isinstance(existing_tags, list):
            existing_tags = [str(existing_tags)]
        if "Automated-Database-Migration-V3" not in existing_tags:
            existing_tags.append("Automated-Database-Migration-V3")
        v3_payload["group_tags"] = existing_tags
        v3_payload.setdefault("assets", [])
        v3_payload.pop("data", None)
        return v3_payload

    def _extract_legacy_worldbook_entries(
        self, filepath: Path, output_dir: Path
    ) -> int:
        try:
            with filepath.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return 0

        entries = data.get("entries", {}) if isinstance(data, dict) else {}
        if not entries and isinstance(data, list):
            entries = {str(index): value for index, value in enumerate(data)}

        compiled_lore_cache: list[dict[str, Any]] = []
        for entry_obj in entries.values():
            if not isinstance(entry_obj, dict):
                continue
            keys = entry_obj.get("keys", entry_obj.get("key", []))
            content = entry_obj.get("content", entry_obj.get("entry", ""))
            activation_keys = self._normalize_keys(keys)
            if activation_keys and str(content).strip():
                compiled_lore_cache.append(
                    {
                        "id": uuid.uuid4().hex[:8],
                        "activation_keys": activation_keys,
                        "lore_entry_payload": str(content),
                    }
                )

        if compiled_lore_cache:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_filename = f"compiled_worldbook_{uuid.uuid4().hex[:6]}.json"
            out_path = output_dir / out_filename
            with out_path.open("w", encoding="utf-8") as out_handle:
                json.dump(
                    {"spec": "worldbook_v1", "entries": compiled_lore_cache},
                    out_handle,
                    indent=2,
                    ensure_ascii=False,
                )
        return len(compiled_lore_cache)

    def _normalize_keys(self, keys: Any) -> list[str]:
        if isinstance(keys, list):
            return [str(key).strip() for key in keys if str(key).strip()]
        if isinstance(keys, str):
            return [chunk.strip() for chunk in keys.split(",") if chunk.strip()]
        return []

    def _is_worldbook_target(self, path: Path) -> bool:
        if path.suffix.lower() == ".entries":
            return True
        lower_name = path.name.lower()
        return "worldbook" in lower_name or "lorebook" in lower_name

    def _emit_log(self, callback, message: str, *, error: bool = False) -> None:
        if callback is not None:
            callback(message)
            return
        if error:
            logger.error(message)
        else:
            logger.info(message)

    def _heuristic_text(self, payload: dict[str, Any]) -> str:
        data = payload.get("data", {}) if payload.get("spec") == "chara_card_v2" else payload
        description = str(data.get("description", ""))
        personality = str(data.get("personality", ""))
        scenario = str(data.get("scenario", ""))
        return f"{description} {personality} {scenario}".lower()

    def _deduce_missing_trope_extensions(self, heuristic_text: str) -> dict[str, Any]:
        if any(
            token in heuristic_text
            for token in ("fake date", "pretend", "contract", "publicity", "script")
        ):
            engine_type = "Fake-Dating"
            weights = {
                "performative_closeness": 4,
                "private_confusion": 2,
                "boundary_panic": 2,
                "angst_meter": 1,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": False,
            }
            trigger_condition = "private_confusion >= 4"
        elif any(
            token in heuristic_text
            for token in ("forbidden", "secret", "taboo", "rule", "exposure", "hidden")
        ):
            engine_type = "Forbidden-Romance"
            weights = {
                "systemic_restraint": 4,
                "stolen_proximity": 2,
                "fear_of_exposure": 4,
                "angst_meter": 3,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": True,
            }
            trigger_condition = "stolen_proximity >= 4"
        elif any(
            token in heuristic_text
            for token in ("ex ", "used to", "again", "history", "heartbreak", "three years")
        ):
            engine_type = "Second-Chance"
            weights = {
                "past_breakup_baggage": 4,
                "protective_pride_shield": 4,
                "residual_heartbreak": 2,
                "angst_meter": 3,
                "lie_active": True,
                "lie_count": 1,
                "distance_locked": False,
            }
            trigger_condition = "residual_heartbreak <= 1 and protective_pride_shield <= 1"
        elif any(token in heuristic_text for token in ("rival", "enemy", "compete")):
            engine_type = "Meet-Ugly"
            weights = {
                "rivalry_heat": 3,
                "repressed_desire": 1,
                "angst_meter": 2,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            }
            trigger_condition = "repressed_desire >= 4"
        elif any(token in heuristic_text for token in ("trap", "lock", "elevator")):
            engine_type = "Forced-Proximity"
            weights = {
                "confinement_stress": 5,
                "hostile_friction_heat": 4,
                "proximity_awareness_acceleration": 2,
                "angst_meter": 1,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": True,
            }
            trigger_condition = "proximity_awareness_acceleration >= 4"
        elif any(
            token in heuristic_text
            for token in ("stranger", "routine", "coffee shop", "face in the crowd")
        ):
            engine_type = "Strangers-to-Lovers"
            weights = {
                "social_distance": 4,
                "observational_interest": 1,
                "vulnerability_thaw": 0,
                "angst_meter": 1,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            }
            trigger_condition = "observational_interest >= 4"
        else:
            engine_type = "Meet-Cute"
            weights = {
                "platonic_trust": 3,
                "romantic_awareness": 1,
                "angst_meter": 0,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            }
            trigger_condition = "romantic_awareness >= 4"

        return {
            "engine_type": engine_type,
            "current_phase": 1,
            "weights": weights,
            "origin_context": {
                "environment_type": "Inferred Workspace Context",
                "incident_summary": "Legacy card configuration update; missing parameters automatically resolved.",
                "spark_token": "Preserved metrics tracking data node links.",
                "unbreakable_tether": "Structural platform necessity bounds.",
            },
            "dialogue_nodes": {
                "phase_4_breaking_point": {
                    "activation_condition": trigger_condition,
                    "dialogue_payload": "I'm sick of pretending this doesn't matter to me.",
                    "action_prompt": "They stand close, cornering your space entirely.",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "Right. Just a mistake. Let's forget it.",
                    "if_player_honest": "I can't go back to how things were before this.",
                },
            },
        }
