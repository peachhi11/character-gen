from __future__ import annotations

import re
import uuid
from typing import Any

from .trope_engine_catalog import LEGACY_ORIGIN_BLOCKS


DEFAULT_ARCHETYPE = "Standard Archetype"
DEFAULT_BODY_LANGUAGE_DESCRIPTOR = (
    "Preserve the physical baseline implied by the native character card fields."
)


def convert_v2_to_v3_with_engine(v2_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a V2 character card payload into a V3 payload while preserving
    any embedded trope engine extension data.
    """
    v2_data = v2_payload.get("data", {})
    v2_extensions = v2_data.get("extensions", {})
    engine_data = v2_extensions.get("trope_engine", {})

    v3_card: dict[str, Any] = {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "id": str(uuid.uuid4()),
        "name": v2_data.get("name", "Unnamed Profile"),
        "description": v2_data.get("description", ""),
        "personality": v2_data.get("personality", ""),
        "scenario": v2_data.get("scenario", ""),
        "first_mes": v2_data.get("first_mes", ""),
        "mes_example": v2_data.get("mes_example", ""),
        "system_prompt": v2_data.get("system_prompt", ""),
        "creator": v2_data.get("creator", ""),
        "version": v2_data.get("character_version", ""),
        "group_tags": list(v2_data.get("tags", [])),
        "assets": [],
        "extensions": {
            "trope_engine": engine_data,
        },
    }

    if "alternate_greetings" in v2_data:
        v3_card["alternate_greetings"] = list(v2_data["alternate_greetings"])

    return v3_card


def extract_trope_engine_card(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a canonical engine-state payload or a V2/V3 character card with a
    trope_engine extension into the canonical engine-state schema consumed by
    the validator and prompt mapper.
    """
    if _is_canonical_engine_state_payload(payload):
        metadata = payload.get("metadata", {})
        engine_type = str(metadata.get("engine_type", "Meet-Cute"))
        payload["trope_engine_weights"] = _normalize_engine_specific_weights(
            engine_type,
            dict(payload.get("trope_engine_weights", {})),
        )
        return payload

    spec = payload.get("spec")
    if spec == "chara_card_v2":
        base = payload.get("data", {})
    elif spec == "chara_card_v3":
        base = payload
    else:
        raise ValueError("Payload is neither a canonical engine-state card nor a supported Character Card V2/V3 payload.")

    extensions = base.get("extensions", {})
    trope_engine = extensions.get("trope_engine")
    if not isinstance(trope_engine, dict):
        raise ValueError("Character card does not contain 'extensions.trope_engine'.")

    name = base.get("name", "Unnamed Profile")
    personality = base.get("personality", "")
    creator_notes = base.get("creator_notes", "")
    first_mes = base.get("first_mes", "")
    mes_example = base.get("mes_example", "")

    canonical: dict[str, Any] = {
        "card_id": payload.get("id")
        or trope_engine.get("card_id")
        or _mint_stable_card_id(name),
        "metadata": {
            "name": name,
            "archetype": creator_notes or personality or DEFAULT_ARCHETYPE,
            "engine_type": trope_engine.get("engine_type", "Meet-Cute"),
            "current_phase": trope_engine.get("current_phase", 1),
        },
        "trope_engine_weights": _normalize_engine_specific_weights(
            str(trope_engine.get("engine_type", "Meet-Cute")),
            dict(trope_engine.get("weights", {})),
        ),
        "origin_context": dict(trope_engine.get("origin_context", {})),
        "dialogue_nodes": {
            "phase_1_baseline": {
                "greeting": first_mes,
                "body_language_descriptor": mes_example
                or personality
                or DEFAULT_BODY_LANGUAGE_DESCRIPTOR,
            },
        },
    }

    for key, value in dict(trope_engine.get("dialogue_nodes", {})).items():
        canonical["dialogue_nodes"][key] = value

    return canonical


def wrap_trope_engine_card_as_v3(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a canonical engine-state payload or a V2/V3 wrapper into a
    Character Card V3 payload with a trope_engine extension.
    """
    spec = payload.get("spec")
    if spec == "chara_card_v3":
        return payload
    if spec == "chara_card_v2":
        return convert_v2_to_v3_with_engine(payload)

    canonical = extract_trope_engine_card(payload)
    metadata = canonical.get("metadata", {})
    origin = canonical.get("origin_context", {})
    dialogue_nodes = canonical.get("dialogue_nodes", {})
    phase_1 = dialogue_nodes.get("phase_1_baseline", {})

    v3_card: dict[str, Any] = {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "id": str(payload.get("card_id") or uuid.uuid4()),
        "name": metadata.get("name", "Unnamed Profile"),
        "description": "",
        "personality": metadata.get("archetype", DEFAULT_ARCHETYPE),
        "scenario": origin.get("environment_type", ""),
        "first_mes": phase_1.get("greeting", ""),
        "mes_example": phase_1.get(
            "body_language_descriptor", DEFAULT_BODY_LANGUAGE_DESCRIPTOR
        ),
        "system_prompt": "",
        "creator": "",
        "version": "main",
        "group_tags": ["Trope-Engine"],
        "assets": [],
        "extensions": {
            "trope_engine": {
                "engine_type": metadata.get("engine_type", "Meet-Cute"),
                "current_phase": metadata.get("current_phase", 1),
                "weights": dict(canonical.get("trope_engine_weights", {})),
                "origin_context": dict(origin),
                "dialogue_nodes": {
                    "phase_4_breaking_point": dict(
                        dialogue_nodes.get("phase_4_breaking_point", {})
                    ),
                    "phase_5_hangover_crisis": dict(
                        dialogue_nodes.get("phase_5_hangover_crisis", {})
                    ),
                },
            }
        },
    }
    return v3_card


def _mint_stable_card_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "unnamed_profile"


def _is_canonical_engine_state_payload(payload: dict[str, Any]) -> bool:
    legacy_origin_keys = {
        key for keys in LEGACY_ORIGIN_BLOCKS.values() for key in keys
    }
    return (
        isinstance(payload, dict)
        and (
            "card_id" in payload
            or "metadata" in payload
        )
        and "metadata" in payload
        and "trope_engine_weights" in payload
        and "dialogue_nodes" in payload
        and (
            "origin_context" in payload
            or any(
                key in payload for key in legacy_origin_keys
            )
        )
    )


def _normalize_engine_specific_weights(
    engine_type: str,
    weights: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(weights)
    if engine_type != "Forced-Proximity":
        return normalized

    legacy_heat = normalized.get("proximity_heat")
    if isinstance(legacy_heat, bool) or not isinstance(legacy_heat, int):
        return normalized

    legacy_heat = max(0, min(5, legacy_heat))
    if "proximity_awareness_acceleration" not in normalized:
        normalized["proximity_awareness_acceleration"] = legacy_heat
    if "hostile_friction_heat" not in normalized:
        normalized["hostile_friction_heat"] = 4
    return normalized
