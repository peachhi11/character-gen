from __future__ import annotations

import operator
import re
from typing import Any

from .card_format_conversion import extract_trope_engine_card


class DialogueTriggerEngine:
    def __init__(self) -> None:
        self.operators = {
            ">=": operator.ge,
            "<=": operator.le,
            ">": operator.gt,
            "<": operator.lt,
            "==": operator.eq,
            "!=": operator.ne,
        }
        self.expr_parser = re.compile(
            r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*(\d+)\s*$"
        )
        self.or_splitter = re.compile(r"\s+or\s+", re.IGNORECASE)
        self.and_splitter = re.compile(r"\s+and\s+", re.IGNORECASE)

    def evaluate_condition_string(
        self, condition_str: str, current_weights: dict[str, Any]
    ) -> bool:
        if self.or_splitter.search(condition_str):
            return any(
                self.evaluate_condition_string(part, current_weights)
                for part in self.or_splitter.split(condition_str)
            )

        if self.and_splitter.search(condition_str):
            return all(
                self.evaluate_condition_string(part, current_weights)
                for part in self.and_splitter.split(condition_str)
            )

        match = self.expr_parser.match(condition_str)
        if not match:
            return False

        variable_key, op_str, target_value_str = match.groups()
        if variable_key not in current_weights:
            return False

        current_value = current_weights[variable_key]
        if isinstance(current_value, bool):
            current_value = 1 if current_value else 0

        try:
            numeric_value = int(current_value)
        except (TypeError, ValueError):
            return False

        op_func = self.operators.get(op_str)
        if op_func is None:
            return False

        return op_func(numeric_value, int(target_value_str))

    def evaluate_all_active_triggers(
        self,
        card_payload: dict[str, Any],
        state_card_data: dict[str, Any],
    ) -> tuple[str, dict[str, str] | None]:
        runtime_card = extract_trope_engine_card(card_payload)
        nodes = runtime_card.get("dialogue_nodes", {})
        weights = dict(state_card_data.get("weights", {}))
        current_phase = int(state_card_data.get("current_phase", 1))

        if current_phase < 4:
            phase_4 = dict(nodes.get("phase_4_breaking_point", {}))
            condition = str(phase_4.get("activation_condition", "")).strip()
            if self.evaluate_condition_string(condition, weights):
                return "EXECUTE_PHASE_4_BREAKING_POINT", {
                    "dialogue": str(phase_4.get("dialogue_payload", "")),
                    "action": str(phase_4.get("action_prompt", "")),
                }

        if current_phase == 4:
            phase_5 = dict(nodes.get("phase_5_hangover_crisis", {}))
            if weights.get("lie_active", False) or int(weights.get("lie_count", 0)) > 0:
                return "EXECUTE_PHASE_5_HANGOVER_CRISIS_DENIAL", {
                    "dialogue": str(phase_5.get("if_player_lied", "")),
                    "action": "[The character pulls back, building an emotional wall of absolute deniability.]",
                }
            return "EXECUTE_PHASE_5_HANGOVER_CRISIS_VULNERABLE", {
                "dialogue": str(phase_5.get("if_player_honest", "")),
                "action": "[The character looks at you with absolute clarity, defenses permanently shattered.]",
            }

        return "CONTINUE_STANDARD_GENERATION", None
