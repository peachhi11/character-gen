from __future__ import annotations

import uuid
from typing import Any

from .card_format_conversion import convert_v2_to_v3_with_engine


class TropeModeSwitcher:
    def identify_and_normalize_payload(
        self, raw_payload: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        spec = raw_payload.get("spec")
        data_block = raw_payload.get("data")

        if spec == "chara_card_v2" or (
            isinstance(data_block, dict) and "description" in data_block
        ):
            return "CHARACTER_CARD_V2", self._normalize_v2_to_v3(raw_payload)

        if spec == "chara_card_v3" and "extensions" in raw_payload:
            return "CHARACTER_CARD_V3", raw_payload

        if "session_id" in raw_payload and "weights" in raw_payload:
            return "ENGINE_STATE_CARD", self._rehydrate_state_as_v3_context(raw_payload)

        raise ValueError(
            "Unknown data structure layout. Failed to identify schema type signature tokens."
        )

    def _normalize_v2_to_v3(self, v2_card: dict[str, Any]) -> dict[str, Any]:
        normalized = convert_v2_to_v3_with_engine(v2_card)
        trope_engine = normalized.setdefault("extensions", {}).get("trope_engine")
        if not isinstance(trope_engine, dict) or not trope_engine:
            normalized["extensions"]["trope_engine"] = self._generate_fallback_engine_block()
        if not normalized.get("group_tags"):
            normalized["group_tags"] = ["V2-Auto-Upgrade"]
        return normalized

    def _rehydrate_state_as_v3_context(
        self, state_card: dict[str, Any]
    ) -> dict[str, Any]:
        session_id = state_card.get("session_id", "unknown_session")
        return {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": state_card.get("card_id", str(uuid.uuid4())),
            "name": f"State Preview Session: {session_id}",
            "description": "[NARRATIVE STATE PREVIEW LAYER]: Detailed properties remain isolated inside session files.",
            "personality": "",
            "scenario": "",
            "first_mes": "",
            "mes_example": "",
            "system_prompt": "",
            "group_tags": ["Active-Session-Load"],
            "assets": [],
            "extensions": {
                "trope_engine": {
                    "engine_type": state_card.get("engine_type", "Meet-Ugly"),
                    "current_phase": state_card.get("current_phase", 1),
                    "weights": dict(state_card.get("weights", {})),
                    "origin_context": {
                        "environment_type": "Session Hydration Context",
                        "incident_summary": "Restored from runtime snapshot file.",
                        "spark_token": "Preserved metrics",
                        "unbreakable_tether": "",
                    },
                    "dialogue_nodes": {
                        "phase_4_breaking_point": {
                            "activation_condition": "romantic_tension >= 4",
                            "dialogue_payload": "",
                            "action_prompt": "",
                        },
                        "phase_5_hangover_crisis": {
                            "if_player_lied": "",
                            "if_player_honest": "",
                        },
                    },
                }
            },
        }

    def _generate_fallback_engine_block(self) -> dict[str, Any]:
        return {
            "engine_type": "Meet-Ugly",
            "current_phase": 1,
            "weights": {
                "rivalry_heat": 3,
                "repressed_desire": 1,
                "angst_meter": 0,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            },
            "origin_context": {
                "environment_type": "",
                "incident_summary": "",
                "spark_token": "",
                "unbreakable_tether": "",
            },
            "dialogue_nodes": {
                "phase_4_breaking_point": {
                    "activation_condition": "rivalry_heat >= 4",
                    "dialogue_payload": "",
                    "action_prompt": "",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "",
                    "if_player_honest": "",
                },
            },
        }
