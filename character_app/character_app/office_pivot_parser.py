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


class TropeOfficePivotParser:
    @staticmethod
    def pivot_fwb_to_office_boss(
        active_session_dict: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """
        Remap a Friends-Benefits runtime session into the safe
        Boardroom-Parity engine after a promotion reshuffle changes the
        public stakes around the relationship.
        """
        old_engine = active_session_dict.get("engine_type")
        if old_engine != "Friends-Benefits":
            raise ValueError(
                "Pivot Error: Expected 'Friends-Benefits', "
                f"received '{old_engine}'."
            )

        session_copy = deepcopy(active_session_dict)
        old_weights = session_copy.get("weights", {})
        if not isinstance(old_weights, dict):
            old_weights = {}

        session_copy["engine_type"] = "Boardroom-Parity"
        session_copy["current_phase"] = 2
        session_copy["last_updated"] = time.time()
        session_copy["weights"] = {
            "promotion_rivalry_heat": 5,
            "favoritism_paranoia": max(
                3,
                _clamp_rating(old_weights.get("boundary_panic_heat", 0), default=0) + 1,
            ),
            "private_fixation": _clamp_rating(
                old_weights.get("private_romantic_fixation", 2),
                default=2,
            ),
            "angst_meter": min(
                5,
                _clamp_rating(old_weights.get("angst_meter", 0), default=0) + 2,
            ),
            "lie_active": True,
            "lie_count": _clamp_counter(old_weights.get("lie_count", 0), default=0) + 1,
            "distance_locked": True,
        }

        directive_prompt = (
            "[SYSTEM PROMPT CRITICAL PARADIGM SHIFT: THE BOARDROOM PARITY]\n"
            "An external promotion event has fired. You are no longer just friends with casual benefits.\n"
            "You are now locked onto parallel executive tracks under direct board scrutiny. Your casual baseline has turned into intense favoritism paranoia and competitive optics.\n"
            "You MUST maintain strict, professional detachment in public areas, masking a volatile private fixation while staying on visibly equal footing."
        )

        return session_copy, directive_prompt
