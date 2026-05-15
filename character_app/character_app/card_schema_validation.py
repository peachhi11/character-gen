from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
from typing import Any

from .trope_engine_catalog import (
    ENGINE_REQUIRED_WEIGHTS,
    ENGINE_OPTION_ORDER,
    LEGACY_ORIGIN_BLOCKS,
    LEGACY_ORIGIN_TO_CANONICAL,
    phase_four_activation_condition,
)

VALID_ENGINES = frozenset(ENGINE_OPTION_ORDER)

BOOLEAN_WEIGHTS = frozenset({"lie_active", "distance_locked", "safeword_breached"})
UNBOUNDED_INT_WEIGHTS = frozenset({"lie_count"})
REQUIRED_GLOBAL_WEIGHTS = ("lie_active", "lie_count", "angst_meter")
REQUIRED_METADATA_FIELDS = ("name", "archetype")

CANONICAL_ORIGIN_FIELDS = (
    "environment_type",
    "incident_summary",
    "spark_token",
    "unbreakable_tether",
)

DIALOGUE_NODE_ALIASES: dict[str, dict[str, str]] = {
    "phase_1_baseline": {
        "body_language": "body_language_descriptor",
    },
    "phase_4_breaking_point": {
        "trigger_condition": "activation_condition",
        "dialogue": "dialogue_payload",
    },
}

DIALOGUE_NODE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "phase_1_baseline": ("greeting", "body_language_descriptor"),
    "phase_4_breaking_point": (
        "activation_condition",
        "dialogue_payload",
        "action_prompt",
    ),
    "phase_5_hangover_crisis": ("if_player_lied", "if_player_honest"),
}

LEGACY_DIALOGUE_MIRRORS: dict[str, dict[str, str]] = {
    "phase_1_baseline": {
        "body_language_descriptor": "body_language",
    },
    "phase_4_breaking_point": {
        "activation_condition": "trigger_condition",
        "dialogue_payload": "dialogue",
    },
}

class InvalidEngineException(ValueError):
    """Raised when a card payload declares an unsupported engine type."""


@dataclass
class CardValidationResult:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_card: dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }
        if self.normalized_card is not None:
            payload["normalized_card"] = self.normalized_card
        if self.success and self.normalized_card:
            payload["message"] = (
                f"Character Card '{self.normalized_card.get('metadata', {}).get('name', '')}' "
                "compiled successfully."
            )
        return payload


class CharacterCardValidator:
    def __init__(self) -> None:
        self.valid_engines = VALID_ENGINES

    def validate_card_json(
        self, json_payload: str | dict[str, Any]
    ) -> CardValidationResult:
        try:
            if isinstance(json_payload, str):
                card = json.loads(json_payload)
            else:
                card = deepcopy(json_payload)
        except json.JSONDecodeError:
            return CardValidationResult(
                status="FAIL",
                errors=["Malformed JSON structure."],
            )

        errors: list[str] = []
        warnings: list[str] = []

        if not isinstance(card, dict):
            return CardValidationResult(
                status="FAIL",
                errors=["Card payload root must be a JSON object."],
            )

        metadata = self._validate_metadata(card, errors)
        engine, engine_source = self._resolve_engine(metadata)
        if engine is None:
            errors.append("Missing valid 'engine_type' in metadata.")
        elif engine not in self.valid_engines:
            errors.append(f"Invalid engine type: '{engine}'.")
        else:
            metadata["engine_type"] = engine
            if engine_source == "base_relationship":
                warnings.append(
                    "Backfilled 'metadata.engine_type' from legacy 'metadata.base_relationship'."
                )

        weights = card.get("trope_engine_weights")
        if not isinstance(weights, dict):
            errors.append("Missing or invalid 'trope_engine_weights' object.")
            weights = {}
            card["trope_engine_weights"] = weights

        if engine in self.valid_engines:
            self._backfill_legacy_weights(engine, weights, warnings)
            self._validate_weights(engine, weights, errors, warnings)
            self._validate_origin(engine, card, errors, warnings)
            self._validate_dialogue_nodes(engine, card, warnings, errors)
            self._validate_logical_sanity(weights, errors)

        status = "FAIL" if errors else "PASS"
        return CardValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            normalized_card=card,
        )

    def _validate_metadata(
        self, card: dict[str, Any], errors: list[str]
    ) -> dict[str, Any]:
        card_id = card.get("card_id")
        if not isinstance(card_id, str) or not card_id.strip():
            errors.append("Missing non-empty top-level 'card_id' string.")

        metadata = card.get("metadata")
        if not isinstance(metadata, dict):
            errors.append("Missing or invalid 'metadata' object.")
            metadata = {}
            card["metadata"] = metadata
            return metadata

        for field_name in REQUIRED_METADATA_FIELDS:
            value = metadata.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"Missing non-empty string 'metadata.{field_name}'."
                )

        current_phase = metadata.get("current_phase")
        if not isinstance(current_phase, int):
            errors.append("Missing integer 'metadata.current_phase'.")
        elif not (1 <= current_phase <= 6):
            errors.append("'metadata.current_phase' must be between 1 and 6.")

        return metadata

    def _resolve_engine(
        self, metadata: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        engine = metadata.get("engine_type")
        if isinstance(engine, str) and engine.strip():
            return engine.strip(), "engine_type"
        fallback = metadata.get("base_relationship")
        if isinstance(fallback, str) and fallback.strip() in self.valid_engines:
            return fallback.strip(), "base_relationship"
        return None, None

    def _validate_weights(
        self,
        engine: str,
        weights: dict[str, Any],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        for key in REQUIRED_GLOBAL_WEIGHTS + ENGINE_REQUIRED_WEIGHTS[engine]:
            if key not in weights:
                errors.append(
                    f"Missing required weight '{key}' for engine '{engine}'."
                )

        for weight_name, value in list(weights.items()):
            if value is None:
                errors.append(
                    f"Weight '{weight_name}' cannot be null."
                )
                continue

            if weight_name in BOOLEAN_WEIGHTS:
                if not isinstance(value, bool):
                    errors.append(
                        f"Weight '{weight_name}' must be a boolean."
                    )
                continue

            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(
                    f"Weight '{weight_name}' must be an integer."
                )
                continue

            if weight_name in UNBOUNDED_INT_WEIGHTS:
                if value < 0:
                    weights[weight_name] = 0
                    warnings.append(
                        f"Clamped negative weight '{weight_name}' from {value} to 0."
                    )
                continue

            clamped = min(5, max(0, value))
            if clamped != value:
                weights[weight_name] = clamped
                warnings.append(
                    f"Clamped out-of-bounds weight '{weight_name}' from {value} to {clamped}."
                )

    def _backfill_legacy_weights(
        self,
        engine: str,
        weights: dict[str, Any],
        warnings: list[str],
    ) -> None:
        if engine != "Forced-Proximity":
            return

        legacy_heat = weights.get("proximity_heat")
        if isinstance(legacy_heat, bool) or not isinstance(legacy_heat, int):
            return

        legacy_heat = max(0, min(5, legacy_heat))
        if "proximity_awareness_acceleration" not in weights:
            weights["proximity_awareness_acceleration"] = legacy_heat
            warnings.append(
                "Backfilled 'proximity_awareness_acceleration' from legacy 'proximity_heat' for engine 'Forced-Proximity'."
            )
        if "hostile_friction_heat" not in weights:
            weights["hostile_friction_heat"] = 4
            warnings.append(
                "Backfilled 'hostile_friction_heat' with legacy default 4 for engine 'Forced-Proximity'."
            )

    def _validate_origin(
        self,
        engine: str,
        card: dict[str, Any],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        origin = card.get("origin_context")
        if isinstance(origin, dict):
            self._validate_origin_context(origin, errors)
            return

        canonical_origin, source_key = self._normalize_legacy_origin(engine, card)
        if canonical_origin is None:
            errors.append(
                f"Missing structural origin context payload object for engine '{engine}'."
            )
            return

        card["origin_context"] = canonical_origin
        warnings.append(
            f"Backfilled canonical 'origin_context' from legacy '{source_key}'."
        )
        self._validate_origin_context(canonical_origin, errors)

    def _normalize_legacy_origin(
        self, engine: str, card: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str | None]:
        alias_map = LEGACY_ORIGIN_TO_CANONICAL[engine]
        for candidate in LEGACY_ORIGIN_BLOCKS[engine]:
            value = card.get(candidate)
            if not isinstance(value, dict):
                continue

            canonical_origin = {
                "environment_type": value.get("type") or engine,
            }
            for legacy_field, canonical_field in alias_map.items():
                if legacy_field == "type":
                    continue
                canonical_origin[canonical_field] = value.get(legacy_field)
            return canonical_origin, candidate
        return None, None

    def _validate_origin_context(
        self, origin: dict[str, Any], errors: list[str]
    ) -> None:
        for field_name in CANONICAL_ORIGIN_FIELDS:
            value = origin.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"Origin field 'origin_context.{field_name}' must be a non-empty string."
                )

    def _validate_dialogue_nodes(
        self,
        engine: str,
        card: dict[str, Any],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        dialogue_nodes = card.get("dialogue_nodes")
        if not isinstance(dialogue_nodes, dict) or not dialogue_nodes:
            errors.append("Missing or invalid 'dialogue_nodes' object.")
            return

        for node_name in DIALOGUE_NODE_REQUIRED_FIELDS:
            if node_name not in dialogue_nodes:
                errors.append(f"Missing required dialogue node '{node_name}'.")

        for node_name, node in dialogue_nodes.items():
            if not isinstance(node, dict):
                errors.append(f"Dialogue node '{node_name}' must be an object.")
                continue

            self._normalize_dialogue_aliases(node_name, node, warnings)

            if node_name not in DIALOGUE_NODE_REQUIRED_FIELDS:
                continue

            for field_name in DIALOGUE_NODE_REQUIRED_FIELDS[node_name]:
                if field_name == "activation_condition":
                    self._validate_activation_condition(
                        engine, node_name, node, warnings, errors
                    )
                    continue

                value = node.get(field_name)
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        f"Dialogue node '{node_name}' requires non-empty string '{field_name}'."
                    )

            self._mirror_dialogue_aliases(node_name, node)

    def _normalize_dialogue_aliases(
        self,
        node_name: str,
        node: dict[str, Any],
        warnings: list[str],
    ) -> None:
        aliases = DIALOGUE_NODE_ALIASES.get(node_name, {})
        for legacy_field, canonical_field in aliases.items():
            if canonical_field in node:
                continue
            if legacy_field not in node:
                continue
            node[canonical_field] = node[legacy_field]
            warnings.append(
                f"Backfilled '{node_name}.{canonical_field}' from legacy '{legacy_field}'."
            )

    def _mirror_dialogue_aliases(self, node_name: str, node: dict[str, Any]) -> None:
        mirrors = LEGACY_DIALOGUE_MIRRORS.get(node_name, {})
        for canonical_field, legacy_field in mirrors.items():
            if canonical_field in node and legacy_field not in node:
                node[legacy_field] = node[canonical_field]

    def _validate_activation_condition(
        self,
        engine: str,
        node_name: str,
        node: dict[str, Any],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        if node_name != "phase_4_breaking_point":
            return

        canonical_trigger = phase_four_activation_condition(engine)
        trigger = node.get("activation_condition")
        if trigger is None:
            node["activation_condition"] = canonical_trigger
            warnings.append(
                f"Injected catalog activation_condition for dialogue node '{node_name}'."
            )
            return

        if isinstance(trigger, str):
            if trigger != canonical_trigger:
                node["activation_condition"] = canonical_trigger
                warnings.append(
                    f"Normalized activation_condition for dialogue node '{node_name}' from catalog rule."
                )
            return

        if not isinstance(trigger, bool):
            errors.append(
                f"Dialogue node '{node_name}' activation_condition must be a string or boolean."
            )
            return

        node["activation_condition"] = canonical_trigger
        warnings.append(
            f"Normalized boolean activation_condition for dialogue node '{node_name}' from catalog rule."
        )

    def _validate_logical_sanity(
        self, weights: dict[str, Any], errors: list[str]
    ) -> None:
        lie_count = weights.get("lie_count", 0)
        lie_active = weights.get("lie_active")
        rivalry_heat = weights.get("rivalry_heat", 0)
        angst_meter = weights.get("angst_meter", 0)
        platonic_trust = weights.get("platonic_trust", 0)
        unresolved_hurt = weights.get("unresolved_hurt", 0)
        systemic_restraint = weights.get("systemic_restraint", 0)
        fear_of_exposure = weights.get("fear_of_exposure", 0)

        if lie_count == 0 and lie_active is True:
            errors.append(
                "Logical Paradox: 'lie_active' cannot be True if 'lie_count' is 0."
            )

        if lie_active is True and "rivalry_heat" in weights and rivalry_heat == 0:
            errors.append(
                "Logical Conflict: 'lie_active' requires active friction; 'rivalry_heat' cannot be 0."
            )

        if (
            "platonic_trust" in weights
            and angst_meter == 5
            and platonic_trust == 5
        ):
            errors.append(
                "Soft-lock Risk: card cannot initialize with both 'angst_meter' and 'platonic_trust' at 5."
            )

        if (
            "past_breakup_baggage" in weights
            and weights.get("past_breakup_baggage", 0) == 5
            and weights.get("protective_pride_shield", 0) == 0
        ):
            errors.append(
                "Logical Conflict: 'Second-Chance' cards with maxed 'past_breakup_baggage' must keep an active protective pride barrier."
            )

        if (
            "systemic_restraint" in weights
            and "fear_of_exposure" in weights
            and systemic_restraint == 5
            and fear_of_exposure == 0
        ):
            errors.append(
                "Soft-lock Risk: 'Forbidden-Romance' cards cannot initialize with absolute restraint and zero exposure fear."
            )
