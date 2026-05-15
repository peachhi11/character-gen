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


class TropeDynamicPivotParser:
    def __init__(self) -> None:
        self.valid_targets = frozenset({"Secret-Relationship", "Runaway-Fiance"})

    def execute_catalyst_pivot(
        self,
        active_session_dict: dict[str, Any],
        target_branch: str,
    ) -> tuple[dict[str, Any], str]:
        """
        Pivot a Fake-Relationship runtime session into a crisis branch without
        dropping session identity or accumulated chat history.
        """
        old_engine = active_session_dict.get("engine_type")
        if old_engine != "Fake-Relationship":
            raise ValueError(
                "Pivot Exception: Expected input 'Fake-Relationship', "
                f"received '{old_engine}'."
            )

        if target_branch not in self.valid_targets:
            raise ValueError(
                f"Pivot Exception: Invalid target branch destination '{target_branch}'."
            )

        session_copy = deepcopy(active_session_dict)
        old_weights = session_copy.get("weights", {})
        if not isinstance(old_weights, dict):
            old_weights = {}

        boundary_panic_source = old_weights.get(
            "boundary_panic_heat",
            old_weights.get("boundary_panic", 0),
        )

        if target_branch == "Secret-Relationship":
            morphed_weights = {
                "systemic_restraint": max(
                    3,
                    _clamp_rating(boundary_panic_source, default=0) + 1,
                ),
                "stolen_proximity": _clamp_rating(
                    old_weights.get("performative_closeness", 2),
                    default=2,
                ),
                "fear_of_exposure": 5,
                "angst_meter": min(
                    5,
                    _clamp_rating(old_weights.get("angst_meter", 0), default=0) + 2,
                ),
                "lie_active": bool(old_weights.get("lie_active", True)),
                "lie_count": _clamp_counter(old_weights.get("lie_count", 0), default=0)
                + 1,
                "distance_locked": True,
            }
            directive_prompt = (
                "[SYSTEM PROMPT DIRECTIVE CRITICAL MUTATION: THE SHATTERED COVER]\n"
                "The fake act has nearly been exposed by an outside party. You have been forced completely underground.\n"
                "The comfortable performative warmth is dead. Every future interaction must be hushed, guarded, "
                "and driven by an extreme fear of exposure, masking an intense private physical hyper-awareness."
            )
        else:
            morphed_weights = {
                "commitment_panic": max(
                    4,
                    _clamp_rating(old_weights.get("private_confusion", 0), default=0)
                    + 1,
                ),
                "abandonment_guilt": min(
                    5,
                    _clamp_rating(boundary_panic_source, default=0) + 2,
                ),
                "lingering_fixation_heat": _clamp_rating(
                    old_weights.get("performative_closeness", 3),
                    default=3,
                ),
                "angst_meter": min(
                    5,
                    _clamp_rating(old_weights.get("angst_meter", 0), default=0) + 1,
                ),
                "lie_active": False,
                "lie_count": _clamp_counter(old_weights.get("lie_count", 0), default=0),
                "distance_locked": False,
            }
            directive_prompt = (
                "[SYSTEM PROMPT DIRECTIVE CRITICAL MUTATION: THE INSTINCTIVE FLIGHT]\n"
                "The pressure of matching the fake performance to real commitment has triggered an immediate crisis.\n"
                "You have abandoned your old status quo completely. Your internal data must prioritize an intense "
                "commitment panic, warring directly against an inescapable, lingering physical fixation on the player."
            )

        session_copy["engine_type"] = target_branch
        session_copy["current_phase"] = 5
        session_copy["last_updated"] = time.time()
        session_copy["weights"] = morphed_weights
        return session_copy, directive_prompt
