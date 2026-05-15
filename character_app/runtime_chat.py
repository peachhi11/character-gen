from __future__ import annotations

from copy import deepcopy
from typing import Any

from .api import APIClient
from .card_format_conversion import extract_trope_engine_card
from .prompt_mapper import LLMPromptMapper
from .runtime_state import BOOLEAN_WEIGHT_KEYS, EngineStateCard


class RuntimeChatService:
    def __init__(
        self,
        api_client: APIClient,
        prompt_mapper: LLMPromptMapper | None = None,
    ) -> None:
        self.api_client = api_client
        self.prompt_mapper = prompt_mapper or LLMPromptMapper()

    def build_runtime_card(
        self,
        card_payload: dict[str, Any],
        session: EngineStateCard,
    ) -> dict[str, Any]:
        runtime_card = extract_trope_engine_card(deepcopy(card_payload))
        metadata = dict(runtime_card.get("metadata", {}))
        metadata["current_phase"] = session.current_phase
        metadata["engine_type"] = session.engine_type or metadata.get(
            "engine_type", "Meet-Cute"
        )
        runtime_card["metadata"] = metadata

        weights = dict(runtime_card.get("trope_engine_weights", {}))
        weights.update(session.weights)
        weights = self._normalize_runtime_weights(weights)
        runtime_card["trope_engine_weights"] = weights
        return runtime_card

    def compile_runtime_prompt(
        self,
        card_payload: dict[str, Any],
        session: EngineStateCard,
    ) -> str:
        runtime_card = self.build_runtime_card(card_payload, session)
        return self.prompt_mapper.compile_system_prompt(runtime_card)

    def generate_response(
        self,
        *,
        card_payload: dict[str, Any],
        session: EngineStateCard,
        user_message: str,
    ) -> tuple[str, str]:
        system_prompt = self.compile_runtime_prompt(card_payload, session)
        response = self.api_client.generate_chat(
            system_prompt=system_prompt,
            chat_history=session.chat_history,
            user_message=user_message,
        )
        return response, system_prompt

    def _normalize_runtime_weights(
        self, weights: dict[str, Any]
    ) -> dict[str, Any]:
        normalized = dict(weights)
        for key in BOOLEAN_WEIGHT_KEYS:
            if key in normalized:
                normalized[key] = bool(normalized.get(key, False))
        if normalized.get("lie_active") is True:
            normalized["lie_count"] = max(1, int(normalized.get("lie_count", 0)))
            normalized["rivalry_heat"] = max(
                1, int(normalized.get("rivalry_heat", 0))
            )
        return normalized
