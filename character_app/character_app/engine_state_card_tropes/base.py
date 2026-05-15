from __future__ import annotations

from typing import Any

Rule = tuple[str, str, int]
RuleSet = Rule | tuple[Rule, ...]
RuleExpression = RuleSet | str


def _condition(rule: RuleExpression) -> str:
    if isinstance(rule, str):
        return rule
    if rule and isinstance(rule[0], tuple):
        return " and ".join(f"{key} {operator} {threshold}" for key, operator, threshold in rule)
    key, operator, threshold = rule
    return f"{key} {operator} {threshold}"


def _slugify(engine_type: str) -> str:
    return engine_type.lower().replace("-", "_")


def _preset(
    *,
    default_name: str,
    archetype: str,
    required_weights: tuple[str, str, str],
    weights: dict[str, int | bool],
    environment_type: str,
    incident_summary: str,
    spark_token: str,
    unbreakable_tether: str,
    phase_four_rule: RuleExpression,
    dialogue_payload: str,
    action_prompt: str,
    if_player_lied: str,
    if_player_honest: str,
    prompt_focus_keys: tuple[str, str],
    prompt_blurb: str,
    legacy_aliases: dict[str, str],
) -> dict[str, Any]:
    return {
        "default_name": default_name,
        "archetype": archetype,
        "required_weights": required_weights,
        "weights": weights,
        "origin_context": {
            "environment_type": environment_type,
            "incident_summary": incident_summary,
            "spark_token": spark_token,
            "unbreakable_tether": unbreakable_tether,
        },
        "dialogue_nodes": {
            "phase_1_baseline": {
                "greeting": "Hello.",
                "body_language_descriptor": "They hold still for a beat too long before answering.",
            },
            "phase_4_breaking_point": {
                "activation_condition": _condition(phase_four_rule),
                "dialogue_payload": dialogue_payload,
                "action_prompt": action_prompt,
            },
            "phase_5_hangover_crisis": {
                "if_player_lied": if_player_lied,
                "if_player_honest": if_player_honest,
            },
        },
        "phase_four_rule": phase_four_rule,
        "prompt_focus_keys": prompt_focus_keys,
        "prompt_blurb": prompt_blurb,
        "legacy_aliases": legacy_aliases,
    }
