from __future__ import annotations

import copy
import re
from typing import Any


class LiveChatLogAnalyzer:
    def __init__(self) -> None:
        self.tension_markers = re.compile(
            r"\b(freeze|breath|stare|flush|heartbeat|clenched|lips|gaze|closer)\b",
            re.IGNORECASE,
        )
        self.confinement_markers = re.compile(
            r"\b(hot|trapped|boxed in|boxed|stuck|air|close|shoulder|wall|elevator)\b",
            re.IGNORECASE,
        )
        self.defensive_markers = re.compile(
            r"\b(mistake|accident|professional|nothing|forget|joke|adrenaline|back away)\b",
            re.IGNORECASE,
        )
        self.vulnerability_markers = re.compile(
            r"\b(scared|terrified|honestly|always|love|truth|stay)\b",
            re.IGNORECASE,
        )

    def analyze_message_turn(
        self,
        player_message: str,
        ai_response: str,
        current_state: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """
        Process one chat turn and return the updated state plus a directive signal.
        """
        updated_state = copy.deepcopy(current_state)
        directive_signal = "MAINTAIN_STATE"

        full_turn_text = f"{player_message} {ai_response}"
        tension_hits = len(self.tension_markers.findall(full_turn_text))
        if tension_hits >= 2:
            if "romantic_tension" in updated_state:
                updated_state["romantic_tension"] = min(
                    5, updated_state.get("romantic_tension", 0) + 1
                )
            elif "repressed_desire" in updated_state:
                updated_state["repressed_desire"] = min(
                    5, updated_state.get("repressed_desire", 0) + 1
                )
            elif "romantic_awareness" in updated_state:
                updated_state["romantic_awareness"] = min(
                    5, updated_state.get("romantic_awareness", 0) + 1
                )

        confinement_hits = len(self.confinement_markers.findall(full_turn_text))
        if confinement_hits >= 2 and "confinement_stress" in updated_state:
            updated_state["confinement_stress"] = min(
                5, updated_state.get("confinement_stress", 0) + 1
            )
            if "proximity_awareness_acceleration" in updated_state:
                updated_state["proximity_awareness_acceleration"] = min(
                    5, updated_state.get("proximity_awareness_acceleration", 0) + 1
                )
            elif "proximity_heat" in updated_state:
                updated_state["proximity_heat"] = min(
                    5, updated_state.get("proximity_heat", 0) + 1
                )

        current_phase = int(updated_state.get("current_phase", 1))
        if current_phase >= 4 or updated_state.get("romantic_tension", 0) >= 4:
            defensive_hits = len(self.defensive_markers.findall(player_message))
            if defensive_hits >= 2 and not updated_state.get("lie_active", False):
                updated_state["lie_active"] = True
                updated_state["lie_count"] = updated_state.get("lie_count", 0) + 1
                updated_state["angst_meter"] = min(
                    5, updated_state.get("angst_meter", 0) + 2
                )
                return updated_state, "TRIGGER_HANGOVER_CRISIS_LIE"

            vulnerable_hits = len(self.vulnerability_markers.findall(player_message))
            if vulnerable_hits >= 2 and updated_state.get("lie_active", False):
                updated_state["lie_active"] = False
                updated_state["angst_meter"] = max(
                    0, updated_state.get("angst_meter", 0) - 3
                )
                updated_state["emotional_depth"] = min(
                    5, updated_state.get("emotional_depth", 0) + 3
                )
                return updated_state, "TRIGGER_LIE_SHATTERED_CLIMAX"

        if updated_state.get("romantic_tension", 0) >= 4 and current_phase < 4:
            updated_state["current_phase"] = 4
            directive_signal = "FORCE_PHASE_4_BREAKING_POINT"
        elif (
            updated_state.get("proximity_awareness_acceleration", 0) >= 4
            or updated_state.get("proximity_heat", 0) >= 4
        ) and current_phase < 4:
            updated_state["current_phase"] = 4
            directive_signal = "FORCE_PHASE_4_BREAKING_POINT"

        return updated_state, directive_signal
