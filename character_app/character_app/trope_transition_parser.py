from __future__ import annotations

from typing import Any


class TropeTransitionParser:
    @staticmethod
    def transition_fake_dating_to_forbidden(
        old_weights: dict[str, Any],
    ) -> dict[str, int | bool]:
        return {
            "systemic_restraint": max(3, int(old_weights.get("boundary_panic", 0)) + 1),
            "stolen_proximity": min(
                5, max(0, int(old_weights.get("performative_closeness", 2)))
            ),
            "fear_of_exposure": max(
                4, min(5, int(old_weights.get("private_confusion", 2)) + 1)
            ),
            "angst_meter": min(5, int(old_weights.get("angst_meter", 0)) + 2),
            "lie_active": bool(old_weights.get("lie_active", False)),
            "lie_count": max(0, int(old_weights.get("lie_count", 0))),
            "distance_locked": True,
        }
