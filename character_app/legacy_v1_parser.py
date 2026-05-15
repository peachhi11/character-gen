from __future__ import annotations

import json
import uuid


class LegacyV1CardParser:
    def parse_and_upgrade_v1(self, v1_json_string: str) -> dict:
        """
        Parse a flat legacy V1 character card and normalize it into a trope-engine
        extended Character Card V3 payload.
        """
        try:
            v1_data = json.loads(v1_json_string)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Provided string payload is not a valid JSON structure."
            ) from exc

        name = v1_data.get("name", "Legacy Character")
        description = v1_data.get("description", "")
        personality = v1_data.get("personality", "")
        scenario = v1_data.get("scenario", "")
        first_mes = v1_data.get("first_mes", "")
        mes_example = v1_data.get("mes_example", "")

        combined_text = f"{description} {personality}".lower()

        if any(marker in combined_text for marker in ("rival", "enemy", "hate")):
            deduced_engine = "Meet-Ugly"
            default_weights = {
                "rivalry_heat": 3,
                "repressed_desire": 1,
                "angst_meter": 2,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            }
            default_origin = {
                "environment_type": "Deduced Competitive Workspace",
                "incident_summary": "Legacy asset auto-migration; adversarial tension profiles inferred.",
                "spark_token": "An unreturned professional evaluation or document.",
                "unbreakable_tether": "Forced institutional co-dependence.",
            }
        elif any(marker in combined_text for marker in ("trap", "lock", "cabin")):
            deduced_engine = "Forced-Proximity"
            default_weights = {
                "confinement_stress": 5,
                "hostile_friction_heat": 4,
                "proximity_awareness_acceleration": 2,
                "angst_meter": 1,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": True,
            }
            default_origin = {
                "environment_type": "Inescapable Physical Enclosure",
                "incident_summary": "Legacy asset auto-migration; spatial confinement inferred.",
                "spark_token": "The single operational heating source or keycard lock.",
                "unbreakable_tether": "Environmental or structural containment.",
            }
        elif any(marker in combined_text for marker in ("crazy", "heist", "run")):
            deduced_engine = "Meet-Crazy"
            default_weights = {
                "chaotic_chemistry": 3,
                "adrenaline_level": 4,
                "angst_meter": 0,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            }
            default_origin = {
                "environment_type": "Absurd Public Disaster",
                "incident_summary": "Legacy asset auto-migration; unhinged introduction sequence inferred.",
                "spark_token": "The matching physical scuff marks or shared ridiculous objects.",
                "unbreakable_tether": "Mutual flight from local authorization forces.",
            }
        else:
            deduced_engine = "Meet-Cute"
            default_weights = {
                "platonic_trust": 3,
                "romantic_awareness": 1,
                "angst_meter": 0,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            }
            default_origin = {
                "environment_type": "Mundane Local Intersection",
                "incident_summary": "Legacy asset auto-migration; stable platonic framework assumed.",
                "spark_token": "A shared coffee order or accidental notebook switch.",
                "unbreakable_tether": "Longstanding neighborhood familiarity.",
            }

        return {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "personality": personality,
            "scenario": scenario,
            "first_mes": first_mes,
            "mes_example": mes_example,
            "system_prompt": "",
            "group_tags": ["Legacy-Upgrade"],
            "assets": [],
            "extensions": {
                "trope_engine": {
                    "engine_type": deduced_engine,
                    "current_phase": 1,
                    "weights": default_weights,
                    "origin_context": default_origin,
                    "dialogue_nodes": {
                        "phase_4_breaking_point": {
                            "activation_condition": "romantic_tension >= 4",
                            "dialogue_payload": "I'm sick of pretending this is just a competition. Look at me.",
                            "action_prompt": "They close the physical distance abruptly, cornering you.",
                        },
                        "phase_5_hangover_crisis": {
                            "if_player_lied": "Right. Just a mistake. Let's act like professionals.",
                            "if_player_honest": "I don't think I can go back to how things were before tonight.",
                        },
                    },
                }
            },
        }
