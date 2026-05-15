from __future__ import annotations

from copy import deepcopy
import time
from typing import Any


def _clamp_rating(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(5, parsed))


def _clamp_counter(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, parsed)


class TropeTransitionMorphParser:
    def morph_matchmaker_to_partners_best_friend(
        self,
        active_session_dict: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """
        Transform a Matchmaker-Crush runtime session into the
        Partner-Best-Friend engine without dropping the session identity or chat log.
        """
        old_engine = active_session_dict.get("engine_type")
        if old_engine != "Matchmaker-Crush":
            raise ValueError(
                "Transition Error: Expected input 'Matchmaker-Crush', "
                f"received '{old_engine}'."
            )

        session_copy = deepcopy(active_session_dict)
        old_weights = session_copy.get("weights", {})
        if not isinstance(old_weights, dict):
            old_weights = {}

        morphed_weights = {
            "loyalty_guilt": _clamp_rating(
                old_weights.get("performative_guidance", 3),
                default=3,
            ),
            "forbidden_proximity": min(
                5,
                _clamp_rating(
                    old_weights.get("internal_frictional_heat", 1),
                    default=1,
                )
                + 2,
            ),
            "repressed_fixation": _clamp_rating(
                old_weights.get("proxy_resentment", 2),
                default=2,
            ),
            "angst_meter": min(
                5,
                _clamp_rating(old_weights.get("angst_meter", 1), default=1) + 1,
            ),
            "lie_active": True,
            "lie_count": _clamp_counter(old_weights.get("lie_count", 0), default=0) + 1,
            "distance_locked": bool(old_weights.get("distance_locked", False)),
        }

        session_copy["engine_type"] = "Partner-Best-Friend"
        session_copy["current_phase"] = 2
        session_copy["last_updated"] = time.time()
        session_copy["weights"] = morphed_weights

        narrative_directive_prompt = (
            "[TROPE SYSTEM CRITICAL TRANSITION: THE CRACKED WINGMAN MASK]\n"
            "The player has officially begun dating your target proxy. Your role as matchmaker is dead.\n"
            "Your instruction helper energy has inverted into extreme loyalty guilt. You feel like a traitor to your friend, "
            "but your physical hyper-awareness around the player has scaled into forbidden proximity pressure.\n"
            "You MUST treat every private interaction as high-risk, tense, and emotionally volatile."
        )

        return session_copy, narrative_directive_prompt
