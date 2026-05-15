from __future__ import annotations

import unittest

from character_app.card_format_conversion import convert_v2_to_v3_with_engine
from character_app.engine_state_card_presets import (
    NEW_ENGINE_STATE_PRESETS,
    build_engine_state_card,
)
from character_app.prompt_mapper import (
    LLMPromptMapper,
    compile_fake_dating_prompt_sub_block,
)
from character_app.trope_engine_catalog import phase_four_activation_condition


class PromptMapperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mapper = LLMPromptMapper()

    def make_payload(self, engine_type: str) -> dict:
        payload = {
            "card_id": "vance_001",
            "metadata": {
                "name": "Julian Vance",
                "archetype": "The Academic Ice-Wall",
                "engine_type": engine_type,
                "current_phase": 4,
            },
            "trope_engine_weights": {
                "angst_meter": 2,
                "lie_active": False,
                "lie_count": 0,
                "distance_locked": False,
            },
            "origin_context": {
                "environment_type": "University Library Archives",
                "incident_summary": "Stole the final critical thesis textbook copy straight out of the player's hands.",
                "spark_token": "The shared research notes with coffee stains across the margins.",
                "unbreakable_tether": "Assigned as co-authors on the career-making publication.",
            },
            "dialogue_nodes": {
                "phase_1_baseline": {
                    "greeting": "Oh, look. The resident expert arrived. Try not to break anything today.",
                    "body_language_descriptor": "They do not look up from their laptop screen, but their typing speed accelerates sharply.",
                },
                "phase_4_breaking_point": {
                    "activation_condition": "romantic_tension >= 4",
                    "dialogue_payload": "I don't hate you. I fight with you because it's the only time you look at me with absolute focus.",
                    "action_prompt": "They step directly into your space, knuckles white against the desk layout.",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "A tactical error driven by cortisol levels. Let's forget it.",
                    "if_player_honest": "Even now? When there's nothing left to hide behind?",
                },
            },
        }
        if engine_type == "Meet-Ugly":
            payload["trope_engine_weights"].update(
                {
                    "rivalry_heat": 4,
                    "repressed_desire": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_desire >= 4"
        elif engine_type == "Meet-Cute":
            payload["trope_engine_weights"].update(
                {
                    "platonic_trust": 4,
                    "romantic_awareness": 2,
                    "fear_of_loss": 3,
                }
            )
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "romantic_awareness >= 4"
        elif engine_type == "Meet-Crazy":
            payload["trope_engine_weights"].update(
                {
                    "chaotic_chemistry": 4,
                    "adrenaline_level": 5,
                    "emotional_depth": 1,
                }
            )
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "chaotic_chemistry >= 4"
        elif engine_type == "Forced-Proximity":
            payload["trope_engine_weights"].update(
                {
                    "confinement_stress": 5,
                    "hostile_friction_heat": 4,
                    "proximity_awareness_acceleration": 2,
                    "distance_locked": True,
                }
            )
        elif engine_type == "Strangers-to-Lovers":
            payload["trope_engine_weights"].update(
                {
                    "social_distance": 4,
                    "observational_focus": 2,
                    "vulnerability_thaw": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Crowded transit station"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "observational_focus >= 4"
        elif engine_type == "Second-Chance":
            payload["trope_engine_weights"].update(
                {
                    "past_breakup_baggage": 4,
                    "protective_pride_shield": 4,
                    "residual_heartbreak": 2,
                    "lie_active": True,
                    "lie_count": 1,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Room still charged with too much shared history"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "residual_heartbreak <= 1 and protective_pride_shield <= 1"
        elif engine_type == "Forbidden-Romance":
            payload["trope_engine_weights"].update(
                {
                    "systemic_restraint": 4,
                    "stolen_proximity": 2,
                    "fear_of_exposure": 4,
                    "distance_locked": True,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "After-hours office with one locked door between desire and fallout"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "stolen_proximity >= 4"
        elif engine_type == "Fake-Dating":
            payload["trope_engine_weights"].update(
                {
                    "performative_closeness": 4,
                    "private_confusion": 2,
                    "boundary_panic": 2,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Doorway just after the audience and excuses finally clear out"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_confusion >= 4"
        elif engine_type == "Best-Friend-Triangle":
            payload["trope_engine_weights"].update(
                {
                    "shared_platonic_trust": 4,
                    "internal_jealousy": 1,
                    "attraction_imbalance": 2,
                    "angst_meter": 2,
                }
            )
            payload["origin_context"]["environment_type"] = "Shared Hometown Commons Lounge"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "internal_jealousy >= 4"
        elif engine_type == "Partner-Best-Friend":
            payload["trope_engine_weights"].update(
                {
                    "loyalty_guilt": 4,
                    "forbidden_proximity": 1,
                    "repressed_fixation": 2,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Engagement party hallway"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_fixation >= 4"
        elif engine_type == "Tug-of-War-Triangle":
            payload["trope_engine_weights"].update(
                {
                    "possessive_heat": 4,
                    "rivalry_panic": 3,
                    "boundary_assertion": 2,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Crowded event floor the moment a rival steps into your orbit"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "rivalry_panic >= 4"
        elif engine_type == "Accidental-Pregnancy":
            payload["trope_engine_weights"].update(
                {
                    "domestic_panic": 4,
                    "forced_co_dependence": 4,
                    "protective_instinct": 2,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Quiet room where obligation just started feeling dangerously personal"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "forced_co_dependence >= 5"
        elif engine_type == "Secret-Lovechild":
            payload["trope_engine_weights"].update(
                {
                    "historical_hurt_index": 4,
                    "parental_shield_drive": 4,
                    "exposure_panic_heat": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Living room after years of silence stopped being sustainable"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "parental_shield_drive >= 5"
        elif engine_type == "One-Night-Stand":
            payload["trope_engine_weights"].update(
                {
                    "physical_hyper_awareness": 5,
                    "social_panic_index": 4,
                    "denial_mask_integrity": 3,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Boardroom doorway after a one-night stand was supposed to stay buried"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "physical_hyper_awareness >= 5"
        elif engine_type == "Matchmaker-Crush":
            payload["trope_engine_weights"].update(
                {
                    "performative_guidance": 5,
                    "proxy_resentment": 1,
                    "physical_hyper_awareness": 1,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Apartment kitchen turned into an impromptu dating strategy station"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "physical_hyper_awareness >= 4"
        elif engine_type == "Relationship-Coach":
            payload["trope_engine_weights"].update(
                {
                    "instructional_intimacy": 4,
                    "transactional_boundary": 4,
                    "private_obsession_heat": 1,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Rooftop bar balcony used as a live flirting classroom"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_obsession_heat >= 4"
        elif engine_type == "Arranged-Marriage":
            payload["trope_engine_weights"].update(
                {
                    "contractual_lock": 5,
                    "clinical_politeness": 4,
                    "undercurrent_fixation": 1,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Penthouse divided by contract and freezing politeness"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "undercurrent_fixation >= 4"
        elif engine_type == "Childhood-Pact":
            payload["trope_engine_weights"].update(
                {
                    "nostalgia_anchor": 5,
                    "pact_relevance_panic": 4,
                    "fear_of_rejection": 3,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Car hood under a quiet streetlight at the midnight deadline"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "pact_relevance_panic >= 4"
        elif engine_type == "Jilted-Bride":
            payload["trope_engine_weights"].update(
                {
                    "public_humiliation": 5,
                    "unresolved_heartbreak": 4,
                    "defensive_pride": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Chapel reception hall after the music has long since died"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "unresolved_heartbreak >= 5"
        elif engine_type == "Runaway-Fiance":
            payload["trope_engine_weights"].update(
                {
                    "commitment_panic": 5,
                    "abandonment_guilt": 4,
                    "lingering_fixation_heat": 2,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Quiet refuge where running finally started to feel optional"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "lingering_fixation_heat >= 4"
        elif engine_type == "Fake-Relationship":
            payload["trope_engine_weights"].update(
                {
                    "performative_closeness": 4,
                    "private_confusion": 3,
                    "boundary_panic_heat": 2,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Shared room built around a long-term cover story nobody can exit casually anymore"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_confusion >= 4"
        elif engine_type == "Secret-Relationship":
            payload["trope_engine_weights"].update(
                {
                    "systemic_restraint": 4,
                    "stolen_proximity": 2,
                    "fear_of_exposure": 4,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Locked office after midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "stolen_proximity >= 4"
        elif engine_type == "Prank-Date":
            payload["trope_engine_weights"].update(
                {
                    "malicious_intent": 4,
                    "shame_collapse": 1,
                    "genuine_fixation": 1,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Diner booth under fluorescent lights after the joke stopped feeling funny"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "shame_collapse >= 4"
        elif engine_type == "Bully-Romance":
            payload["trope_engine_weights"].update(
                {
                    "overt_antagonism": 4,
                    "buried_fixation": 2,
                    "power_dominance": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Locker-lined hallway where hostility has always been the easiest language to reach for first"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "buried_fixation >= 4"
        elif engine_type == "Tortured-Hero":
            payload["trope_engine_weights"].update(
                {
                    "internal_trauma": 5,
                    "emotional_detachment": 4,
                    "rescue_resistance": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Safehouse infirmary"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "emotional_detachment <= 1"
        elif engine_type == "Hate-to-Love":
            payload["trope_engine_weights"].update(
                {
                    "hostile_friction": 4,
                    "physical_attraction": 1,
                    "repressed_heat": 2,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Boardroom argument at midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_heat >= 4"
        elif engine_type == "Revenge-Romance":
            payload["trope_engine_weights"].update(
                {
                    "manipulation_drive": 5,
                    "network_infiltration": 4,
                    "loyalty_sabotage_heat": 1,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Private dinner room overlooking the target family's corporate floor"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "loyalty_sabotage_heat >= 4"
        elif engine_type == "Blackmail-Date":
            payload["trope_engine_weights"].update(
                {
                    "coercive_leverage": 4,
                    "hostile_compliance": 3,
                    "power_inversion": 1,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Dimly lit VIP restaurant alcove"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "power_inversion >= 4"
        elif engine_type == "The-Bet":
            payload["trope_engine_weights"].update(
                {
                    "cynical_wager_leverage": 4,
                    "peer_validation_drive": 3,
                    "guilt_conversion_heat": 0,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Loud high-density college campus bar"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "guilt_conversion_heat >= 4"
        elif engine_type == "Mafia-Crime":
            payload["trope_engine_weights"].update(
                {
                    "underworld_dominance": 5,
                    "lethal_risk_factor": 4,
                    "protective_obsession": 2,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private club war room"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "protective_obsession >= 4"
        elif engine_type == "Captive-Captor":
            payload["trope_engine_weights"].update(
                {
                    "confinement_stress": 5,
                    "power_asymmetry": 5,
                    "trauma_bonding": 1,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Secluded mountain safehouse vault"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "trauma_bonding >= 4"
        elif engine_type == "Escort-Transaction":
            payload["trope_engine_weights"].update(
                {
                    "transactional_boundary": 5,
                    "performative_intimacy": 4,
                    "private_numbness": 3,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "High-society gala reception"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_numbness <= 1"
        elif engine_type == "Sex-Club":
            payload["trope_engine_weights"].update(
                {
                    "sensory_exposure": 4,
                    "performative_heat": 3,
                    "exclusive_fixation": 1,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Subterranean velvet lounge"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "exclusive_fixation >= 4"
        elif engine_type == "Virgin-Auction":
            payload["trope_engine_weights"].update(
                {
                    "financial_leverage": 5,
                    "ownership_heat": 4,
                    "protective_safeguard": 1,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "High-society underworld auction gala"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "protective_safeguard >= 4"
        elif engine_type == "BDSM-Exchange":
            payload["trope_engine_weights"].update(
                {
                    "power_exchange_heat": 4,
                    "consent_restraint": 3,
                    "aftercare_safety": 2,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private dungeon suite"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "power_exchange_heat >= 4"
        elif engine_type == "Rescue-Romance":
            payload["trope_engine_weights"].update(
                {
                    "protector_drive": 5,
                    "trauma_thaw": 1,
                    "vulnerability_spike": 2,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Secured remote mountain cabin"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "trauma_thaw >= 4"
        elif engine_type == "Step-Sibling":
            payload["trope_engine_weights"].update(
                {
                    "domestic_lock": 4,
                    "family_friction": 4,
                    "repressed_fixation": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Upstairs hallway outside a bedroom"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_fixation >= 4"
        elif engine_type == "Teacher-Parent":
            payload["trope_engine_weights"].update(
                {
                    "professional_boundary": 4,
                    "parental_protective_drive": 3,
                    "situational_awkwardness": 2,
                    "angst_meter": 2,
                }
            )
            payload["origin_context"]["environment_type"] = "Parent-teacher conference room"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "professional_boundary <= 1"
        elif engine_type == "Academic-Rivals":
            payload["trope_engine_weights"].update(
                {
                    "academic_risk_factor": 5,
                    "hidden_proximity": 4,
                    "evaluation_panic": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Seminar room after hours"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "hidden_proximity >= 5"
        elif engine_type == "Teacher-Student":
            payload["trope_engine_weights"].update(
                {
                    "academic_risk_factor": 5,
                    "hidden_proximity": 4,
                    "evaluation_panic": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Lecture hall after hours"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "hidden_proximity >= 5"
        elif engine_type == "Boardroom-Parity":
            payload["trope_engine_weights"].update(
                {
                    "promotion_rivalry_heat": 4,
                    "favoritism_paranoia": 4,
                    "private_fixation": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Executive office suite after a late board review"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_fixation >= 4"
        elif engine_type == "Boss-Employee":
            payload["trope_engine_weights"].update(
                {
                    "corporate_asymmetry": 5,
                    "favoritism_paranoia": 4,
                    "private_fixation": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Executive elevator"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_fixation >= 4"
        elif engine_type == "Age-Gap":
            payload["trope_engine_weights"].update(
                {
                    "generational_variance": 4,
                    "protective_seniority": 4,
                    "social_disapproval_heat": 3,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Townhouse doorway at midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "protective_seniority >= 5"
        elif engine_type == "Doctor-Patient":
            payload["trope_engine_weights"].update(
                {
                    "ethical_restraint": 5,
                    "clinical_objectivity": 4,
                    "vulnerability_spike": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private examination room"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "clinical_objectivity <= 1"
        elif engine_type == "Clinical-Consult":
            payload["trope_engine_weights"].update(
                {
                    "ethical_restraint": 5,
                    "clinical_objectivity": 4,
                    "vulnerability_spike": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private consultation room off a trauma ward"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "clinical_objectivity <= 1"
        elif engine_type == "Lawyer-Client":
            payload["trope_engine_weights"].update(
                {
                    "legal_stakes_heat": 5,
                    "confidential_proximity": 4,
                    "conflict_of_interest": 3,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Late-night deposition office"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "confidential_proximity >= 5"
        elif engine_type == "Co-Counsel":
            payload["trope_engine_weights"].update(
                {
                    "legal_stakes_heat": 5,
                    "confidential_proximity": 4,
                    "conflict_of_interest": 3,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Privilege-walled war room behind closed blinds"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "confidential_proximity >= 5"
        elif engine_type == "Billionaire-Playboy":
            payload["trope_engine_weights"].update(
                {
                    "capital_leverage": 5,
                    "media_scrutiny_heat": 4,
                    "exclusive_fixation": 1,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Town car behind a gala"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "exclusive_fixation >= 4"
        elif engine_type == "Office-Benefits":
            payload["trope_engine_weights"].update(
                {
                    "transactional_casualty": 4,
                    "cubicle_proximity": 4,
                    "private_fixation": 1,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Breakroom and copy room loop"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_fixation >= 4"
        elif engine_type == "Office-Rivals":
            payload["trope_engine_weights"].update(
                {
                    "promotion_rivalry_heat": 4,
                    "hostile_friction": 4,
                    "competence_respect": 2,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Sales floor at midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "competence_respect >= 4"
        elif engine_type == "Cooking-Show":
            payload["trope_engine_weights"].update(
                {
                    "sensory_exposure": 4,
                    "media_performance_heat": 3,
                    "timer_stress_boundary": 3,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Studio kitchen station"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "sensory_exposure >= 4"
        elif engine_type == "Pack-Commander":
            payload["trope_engine_weights"].update(
                {
                    "hierarchy_dominance": 5,
                    "pack_protective_drive": 4,
                    "territorial_panic": 1,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Council chamber after a rival challenge"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "territorial_panic >= 4"
        elif engine_type == "Sanctuary-Refuge":
            payload["trope_engine_weights"].update(
                {
                    "independent_resistance_mask": 5,
                    "sanctuary_drive": 3,
                    "exposure_panic": 2,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Hidden safehouse lounge"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "sanctuary_drive >= 4 and exposure_panic >= 4"
        elif engine_type == "Instinct-Override":
            payload["trope_engine_weights"].update(
                {
                    "instinct_pressure": 5,
                    "accelerated_proximity": 5,
                    "rational_resistance": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Secure operations room after a breach alert"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "rational_resistance <= 1"
        elif engine_type == "Bloodline-Obligation":
            payload["trope_engine_weights"].update(
                {
                    "bloodline_obligation": 5,
                    "council_honor_code": 4,
                    "private_emotional_capture": 1,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Ancestral manor archive"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_emotional_capture >= 4"
        elif engine_type == "Grounding-Anchor":
            payload["trope_engine_weights"].update(
                {
                    "grounding_reliability": 5,
                    "emotional_anchoring": 4,
                    "crisis_mitigation": 3,
                    "angst_meter": 1,
                    "lie_active": False,
                    "lie_count": 0,
                    "distance_locked": False,
                }
            )
            payload["origin_context"]["environment_type"] = "Quiet apartment kitchen after a panic spiral"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "grounding_reliability >= 5 and crisis_mitigation >= 4"
        elif engine_type == "Band-Brothers":
            payload["trope_engine_weights"].update(
                {
                    "fraternal_loyalty_shield": 5,
                    "tactical_proximity": 4,
                    "protective_obsession": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Forward operating lineup"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "protective_obsession >= 4"
        elif engine_type == "Harem-Friends":
            payload["trope_engine_weights"].update(
                {
                    "group_status_quo_friction": 4,
                    "proxy_competitive_panic": 3,
                    "jealousy_heat": 1,
                    "angst_meter": 2,
                }
            )
            payload["origin_context"]["environment_type"] = "Loud group circle where fake peace is starting to crack"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "jealousy_heat >= 4"
        elif engine_type == "Polyamory-Love":
            payload["trope_engine_weights"].update(
                {
                    "multi_party_equilibrium": 4,
                    "boundary_negotiation": 4,
                    "psychological_safety": 2,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Circular table set for a conversation that was supposed to stay calm"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "boundary_negotiation <= 1"
        elif engine_type == "MMF-Triad":
            payload["trope_engine_weights"].update(
                {
                    "alpha_friction_heat": 4,
                    "shared_possessive_heat": 4,
                    "synchronized_obsession": 1,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Locked private suite with both exits already watched"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "synchronized_obsession >= 4"
        elif engine_type == "MFM-Triad":
            payload["trope_engine_weights"].update(
                {
                    "parallel_attraction": 4,
                    "truce_buffer_comfort": 4,
                    "protective_safeguard": 2,
                    "angst_meter": 2,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Leather sectional arranged to feel intentionally safe"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "parallel_attraction >= 4"
        elif engine_type == "MFF-Triad":
            payload["trope_engine_weights"].update(
                {
                    "domestic_rebalancing": 4,
                    "dual_female_friction": 3,
                    "emotional_equilibrium": 2,
                    "angst_meter": 2,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Master bedroom double doors closed against the rest of the house"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "domestic_rebalancing >= 4"
        elif engine_type == "Sovereign-Selection":
            payload["trope_engine_weights"].update(
                {
                    "suitor_density_load": 4,
                    "selection_stress_index": 4,
                    "horizontal_ranking_score": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Mantelpiece and sitting room built for a courtly performance nobody can sustain cleanly anymore"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "selection_stress_index >= 4"
        elif engine_type == "No-Feelings":
            payload["trope_engine_weights"].update(
                {
                    "emotional_detachment": 5,
                    "physical_hyper_awareness": 4,
                    "boundary_panic_heat": 1,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Apartment door at sunrise"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "boundary_panic_heat >= 4"
        elif engine_type == "Friends-Benefits":
            payload["trope_engine_weights"].update(
                {
                    "platonic_baseline_trust": 4,
                    "contractual_intimacy": 4,
                    "private_romantic_fixation": 1,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Shared couch after midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_romantic_fixation >= 4"
        elif engine_type == "Friends-Lovers":
            payload["trope_engine_weights"].update(
                {
                    "historical_security": 5,
                    "fear_of_relationship_loss": 4,
                    "physical_awareness_shift": 1,
                    "angst_meter": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Best-friend living room"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "physical_awareness_shift >= 4"
        elif engine_type == "Accidental-Adultery":
            payload["trope_engine_weights"].update(
                {
                    "moral_crisis_heat": 5,
                    "hidden_marital_baggage": 4,
                    "guilt_conversion_index": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Dimly lit after-hours office suite"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = (
                "guilt_conversion_index >= 4 or moral_crisis_heat == 5 and guilt_conversion_index >= 3"
            )
        else:
            try:
                return build_engine_state_card(
                    engine_type,
                    card_id="vance_001",
                    name="Julian Vance",
                    current_phase=4,
                )
            except KeyError as exc:
                raise ValueError(engine_type) from exc
        return payload

    def test_compile_system_prompt_renders_canonical_payload(self) -> None:
        prompt = self.mapper.compile_system_prompt(self.make_payload("Meet-Ugly"))

        self.assertIn("[ROLEPLAY EMULATION ENGINE INSTRUCTIONS]", prompt)
        self.assertIn("- Name: Julian Vance", prompt)
        self.assertIn("- Archetype: The Academic Ice-Wall", prompt)
        self.assertIn("- Trope Engine Variant: Meet-Ugly", prompt)
        self.assertIn("rivalry_heat: 4", prompt)
        self.assertIn("[CRITICAL CONSTRAINT] 'lie_active' is true", prompt)
        self.assertIn("[ENVIRONMENTAL CONSTRAINT] 'distance_locked' is true", prompt)
        self.assertIn("[ENGINE SPECIFIC: MEET-UGLY]", prompt)
        self.assertIn("University Library Archives", prompt)
        self.assertIn(phase_four_activation_condition("Meet-Ugly"), prompt)
        self.assertIn("A tactical error driven by cortisol levels. Let's forget it.", prompt)
        self.assertIn("NEVER step out of character or speak for the user", prompt)

    def test_compile_system_prompt_uses_normalized_legacy_aliases(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        del payload["origin_context"]
        payload["meet_ugly_origin"] = {
            "type": "University Library Archives",
            "incident": "Stole the final critical thesis textbook copy straight out of the player's hands.",
            "spark_token": "The shared research notes with coffee stains across the margins.",
            "tether": "Assigned as co-authors on the career-making publication.",
        }
        del payload["dialogue_nodes"]["phase_1_baseline"]["body_language_descriptor"]
        payload["dialogue_nodes"]["phase_1_baseline"][
            "body_language"
        ] = "They do not look up from their laptop screen, but their typing speed accelerates sharply."
        del payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"]
        del payload["dialogue_nodes"]["phase_4_breaking_point"]["dialogue_payload"]
        payload["dialogue_nodes"]["phase_4_breaking_point"][
            "trigger_condition"
        ] = "romantic_tension >= 4"
        payload["dialogue_nodes"]["phase_4_breaking_point"][
            "dialogue"
        ] = "I don't hate you. I fight with you because it's the only time you look at me with absolute focus."

        prompt = self.mapper.compile_system_prompt(payload)

        self.assertIn("University Library Archives", prompt)
        self.assertIn(phase_four_activation_condition("Meet-Ugly"), prompt)
        self.assertIn(
            "I don't hate you. I fight with you because it's the only time you look at me with absolute focus.",
            prompt,
        )
        self.assertIn(
            "They do not look up from their laptop screen, but their typing speed accelerates sharply.",
            prompt,
        )

    def test_compile_system_prompt_accepts_wrapped_v2_and_v3_cards(self) -> None:
        base_payload = self.make_payload("Meet-Ugly")
        wrapped_v2 = {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": base_payload["metadata"]["name"],
                "description": "An exacting academic rival with polished edges.",
                "personality": base_payload["metadata"]["archetype"],
                "scenario": base_payload["origin_context"]["environment_type"],
                "first_mes": base_payload["dialogue_nodes"]["phase_1_baseline"][
                    "greeting"
                ],
                "mes_example": base_payload["dialogue_nodes"]["phase_1_baseline"][
                    "body_language_descriptor"
                ],
                "extensions": {
                    "trope_engine": {
                        "engine_type": base_payload["metadata"]["engine_type"],
                        "current_phase": base_payload["metadata"]["current_phase"],
                        "weights": base_payload["trope_engine_weights"],
                        "origin_context": base_payload["origin_context"],
                        "dialogue_nodes": {
                            "phase_4_breaking_point": base_payload["dialogue_nodes"][
                                "phase_4_breaking_point"
                            ],
                            "phase_5_hangover_crisis": base_payload["dialogue_nodes"][
                                "phase_5_hangover_crisis"
                            ],
                        },
                    }
                },
            },
        }
        wrapped_v3 = convert_v2_to_v3_with_engine(wrapped_v2)

        prompt_v2 = self.mapper.compile_system_prompt(wrapped_v2)
        prompt_v3 = self.mapper.compile_system_prompt(wrapped_v3)

        self.assertIn("Trope Engine Variant: Meet-Ugly", prompt_v2)
        self.assertIn("Trope Engine Variant: Meet-Ugly", prompt_v3)
        self.assertIn("University Library Archives", prompt_v2)
        self.assertIn("University Library Archives", prompt_v3)

    def test_compile_system_prompt_rejects_invalid_card(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        payload["trope_engine_weights"]["rivalry_heat"] = 0

        with self.assertRaises(ValueError) as error:
            self.mapper.compile_system_prompt(payload)

        self.assertIn("Character card validation failed", str(error.exception))
        self.assertIn("Logical Conflict", str(error.exception))

    def test_compile_system_prompt_renders_engine_specific_variants(self) -> None:
        meet_cute = self.mapper.compile_system_prompt(self.make_payload("Meet-Cute"))
        meet_crazy = self.mapper.compile_system_prompt(self.make_payload("Meet-Crazy"))
        forced = self.mapper.compile_system_prompt(self.make_payload("Forced-Proximity"))

        self.assertIn("[ENGINE SPECIFIC: MEET-CUTE]", meet_cute)
        self.assertIn("platonic_trust is 4/5", meet_cute)
        self.assertIn("[ENGINE SPECIFIC: MEET-CRAZY]", meet_crazy)
        self.assertIn("adrenaline_level is 5/5", meet_crazy)
        self.assertIn("[ENGINE SPECIFIC: FORCED-PROXIMITY]", forced)
        self.assertIn("confinement_stress is 5/5", forced)
        self.assertIn("proximity_awareness_acceleration is 2/5", forced)

    def test_compile_system_prompt_renders_advanced_engine_variants(self) -> None:
        strangers = self.mapper.compile_system_prompt(
            self.make_payload("Strangers-to-Lovers")
        )
        second = self.mapper.compile_system_prompt(self.make_payload("Second-Chance"))
        forbidden = self.mapper.compile_system_prompt(
            self.make_payload("Forbidden-Romance")
        )
        fake = self.mapper.compile_system_prompt(self.make_payload("Fake-Dating"))

        self.assertIn("[ENGINE SPECIFIC: STRANGERS-TO-LOVERS]", strangers)
        self.assertIn("social_distance is 4/5", strangers)
        self.assertIn("[ENGINE SPECIFIC: SECOND-CHANCE]", second)
        self.assertIn("past_breakup_baggage is 4/5", second)
        self.assertIn("[ENGINE SPECIFIC: FORBIDDEN-ROMANCE]", forbidden)
        self.assertIn("fear_of_exposure is 4/5", forbidden)
        self.assertIn("[TROPE ENGINE DIRECTIVE: THE FAKE-DATING MASK]", fake)
        self.assertIn("[ACTIVE LAYER: PRIVATE ISOLATION DETECTED]", fake)

    def test_compile_system_prompt_renders_specialized_engine_variants(self) -> None:
        expectations = {
            "Best-Friend-Triangle": ("[ENGINE SPECIFIC: BEST-FRIEND-TRIANGLE]", "internal_jealousy is 1/5"),
            "Partner-Best-Friend": ("[ENGINE SPECIFIC: PARTNER-BEST-FRIEND]", "repressed_fixation is 2/5"),
            "Tug-of-War-Triangle": ("[ENGINE SPECIFIC: TUG-OF-WAR-TRIANGLE]", "rivalry_panic is 3/5"),
            "Accidental-Pregnancy": ("[ENGINE SPECIFIC: ACCIDENTAL-PREGNANCY]", "forced_co_dependence is 4/5"),
            "Secret-Lovechild": ("[ENGINE SPECIFIC: SECRET-LOVECHILD]", "parental_shield_drive is 4/5"),
            "One-Night-Stand": ("[ENGINE SPECIFIC: ONE-NIGHT-STAND]", "social_panic_index is 4/5"),
            "Matchmaker-Crush": ("[ENGINE SPECIFIC: MATCHMAKER-CRUSH]", "physical_hyper_awareness is 1/5"),
            "Relationship-Coach": ("[ENGINE SPECIFIC: RELATIONSHIP-COACH]", "private_obsession_heat is 1/5"),
            "Arranged-Marriage": ("[ENGINE SPECIFIC: ARRANGED-MARRIAGE]", "clinical_politeness is 4/5"),
            "Childhood-Pact": ("[ENGINE SPECIFIC: CHILDHOOD-PACT]", "pact_relevance_panic is 4/5"),
        }

        for engine_type, (marker, detail) in expectations.items():
            with self.subTest(engine_type=engine_type):
                prompt = self.mapper.compile_system_prompt(self.make_payload(engine_type))
                self.assertIn(marker, prompt)
                self.assertIn(detail, prompt)

    def test_compile_system_prompt_renders_dark_romance_engine_variants(self) -> None:
        expectations = {
            "Jilted-Bride": ("[ENGINE SPECIFIC: JILTED-BRIDE]", "unresolved_heartbreak is 4/5"),
            "Runaway-Fiance": ("[ENGINE SPECIFIC: RUNAWAY-FIANCE]", "lingering_fixation_heat is 2/5"),
            "Fake-Relationship": ("[ENGINE SPECIFIC: FAKE-RELATIONSHIP]", "private_confusion is 3/5"),
            "Secret-Relationship": ("[ENGINE SPECIFIC: SECRET-RELATIONSHIP]", "fear_of_exposure is 4/5"),
            "Prank-Date": ("[ENGINE SPECIFIC: PRANK-DATE]", "shame_collapse is 1/5"),
            "Bully-Romance": ("[ENGINE SPECIFIC: BULLY-ROMANCE]", "buried_fixation is 2/5"),
            "Tortured-Hero": ("[ENGINE SPECIFIC: TORTURED-HERO]", "emotional_detachment is 4/5"),
            "Hate-to-Love": ("[ENGINE SPECIFIC: HATE-TO-LOVE]", "repressed_heat is 2/5"),
            "Revenge-Romance": ("[ENGINE SPECIFIC: REVENGE-ROMANCE]", "loyalty_sabotage_heat is 1/5"),
            "Blackmail-Date": ("[ENGINE SPECIFIC: BLACKMAIL-DATE]", "power_inversion is 1/5"),
            "The-Bet": ("[ENGINE SPECIFIC: THE-BET]", "guilt_conversion_heat is 0/5"),
            "Ugly-Duckling": ("[ENGINE SPECIFIC: UGLY-DUCKLING]", "transformation_shock is 3/5"),
            "Mafia-Crime": ("[ENGINE SPECIFIC: MAFIA-CRIME]", "protective_obsession is 2/5"),
            "Captive-Captor": ("[ENGINE SPECIFIC: CAPTIVE-CAPTOR]", "trauma_bonding is 1/5"),
            "Escort-Transaction": ("[ENGINE SPECIFIC: ESCORT-TRANSACTION]", "private_numbness is 3/5"),
            "Sex-Club": ("[ENGINE SPECIFIC: SEX-CLUB]", "exclusive_fixation is 1/5"),
            "Virgin-Auction": ("[ENGINE SPECIFIC: VIRGIN-AUCTION]", "protective_safeguard is 1/5"),
            "BDSM-Exchange": ("[ENGINE SPECIFIC: BDSM-EXCHANGE]", "aftercare_safety is 2/5"),
            "Rescue-Romance": ("[ENGINE SPECIFIC: RESCUE-ROMANCE]", "trauma_thaw is 1/5"),
            "Step-Sibling": ("[ENGINE SPECIFIC: STEP-SIBLING]", "repressed_fixation is 2/5"),
        }

        for engine_type, (marker, detail) in expectations.items():
            with self.subTest(engine_type=engine_type):
                prompt = self.mapper.compile_system_prompt(self.make_payload(engine_type))
                self.assertIn(marker, prompt)
                self.assertIn(detail, prompt)

    def test_compile_system_prompt_renders_authority_and_group_engine_variants(self) -> None:
        expectations = {
            "Teacher-Parent": ("[ENGINE SPECIFIC: TEACHER-PARENT]", "professional_boundary is 4/5"),
            "Academic-Rivals": ("[ENGINE SPECIFIC: ACADEMIC-RIVALS]", "hidden_proximity is 4/5"),
            "Teacher-Student": ("[ENGINE SPECIFIC: TEACHER-STUDENT]", "hidden_proximity is 4/5"),
            "Boardroom-Parity": ("[ENGINE SPECIFIC: BOARDROOM-PARITY]", "favoritism_paranoia is 4/5"),
            "Boss-Employee": ("[ENGINE SPECIFIC: BOSS-EMPLOYEE]", "favoritism_paranoia is 4/5"),
            "Age-Gap": ("[ENGINE SPECIFIC: AGE-GAP]", "protective_seniority is 4/5"),
            "Doctor-Patient": ("[ENGINE SPECIFIC: DOCTOR-PATIENT]", "clinical_objectivity is 4/5"),
            "Clinical-Consult": ("[ENGINE SPECIFIC: CLINICAL-CONSULT]", "clinical_objectivity is 4/5"),
            "Lawyer-Client": ("[ENGINE SPECIFIC: LAWYER-CLIENT]", "confidential_proximity is 4/5"),
            "Co-Counsel": ("[ENGINE SPECIFIC: CO-COUNSEL]", "confidential_proximity is 4/5"),
            "Billionaire-Playboy": ("[ENGINE SPECIFIC: BILLIONAIRE-PLAYBOY]", "exclusive_fixation is 1/5"),
            "Office-Benefits": ("[ENGINE SPECIFIC: OFFICE-BENEFITS]", "private_fixation is 1/5"),
            "Office-Rivals": ("[ENGINE SPECIFIC: OFFICE-RIVALS]", "competence_respect is 2/5"),
            "Cooking-Show": ("[ENGINE SPECIFIC: COOKING-SHOW]", "media_performance_heat is 3/5"),
            "Pack-Commander": ("[ENGINE SPECIFIC: PACK-COMMANDER]", "territorial_panic is 1/5"),
            "Sanctuary-Refuge": ("[ENGINE SPECIFIC: SANCTUARY-REFUGE]", "sanctuary_drive is 3/5"),
            "Instinct-Override": ("[ENGINE SPECIFIC: INSTINCT-OVERRIDE]", "rational_resistance is 3/5"),
            "Bloodline-Obligation": ("[ENGINE SPECIFIC: BLOODLINE-OBLIGATION]", "private_emotional_capture is 1/5"),
            "Grounding-Anchor": ("[ENGINE SPECIFIC: GROUNDING-ANCHOR]", "crisis_mitigation is 3/5"),
            "Band-Brothers": ("[ENGINE SPECIFIC: BAND-BROTHERS]", "protective_obsession is 2/5"),
            "Harem-Friends": ("[ENGINE SPECIFIC: HAREM-FRIENDS]", "jealousy_heat is 1/5"),
            "Polyamory-Love": ("[ENGINE SPECIFIC: POLYAMORY-LOVE]", "boundary_negotiation is 4/5"),
            "MMF-Triad": ("[ENGINE SPECIFIC: MMF-TRIAD]", "synchronized_obsession is 1/5"),
            "MFM-Triad": ("[ENGINE SPECIFIC: MFM-TRIAD]", "parallel_attraction is 4/5"),
            "MFF-Triad": ("[ENGINE SPECIFIC: MFF-TRIAD]", "dual_female_friction is 3/5"),
            "Sovereign-Selection": ("[ENGINE SPECIFIC: SOVEREIGN-SELECTION]", "selection_stress_index is 4/5"),
            "No-Feelings": ("[ENGINE SPECIFIC: NO-FEELINGS]", "boundary_panic_heat is 1/5"),
            "Friends-Benefits": ("[ENGINE SPECIFIC: FRIENDS-BENEFITS]", "private_romantic_fixation is 1/5"),
            "Friends-Lovers": ("[ENGINE SPECIFIC: FRIENDS-LOVERS]", "physical_awareness_shift is 1/5"),
            "Childhood-Reunion": ("[ENGINE SPECIFIC: CHILDHOOD-REUNION]", "time_gap_divergence is 4/5"),
            "High-School-Sweethearts": ("[ENGINE SPECIFIC: HIGH-SCHOOL-SWEETHEARTS]", "adult_evaluation_friction is 2/5"),
            "Jock-Tutor": ("[ENGINE SPECIFIC: JOCK-TUTOR]", "intellectual_attraction is 1/5"),
            "New-Old-Flame": ("[ENGINE SPECIFIC: NEW-OLD-FLAME]", "nostalgic_relapse_drive is 3/5"),
            "Accidental-Adultery": ("[ENGINE SPECIFIC: ACCIDENTAL-ADULTERY]", "guilt_conversion_index is 3/5"),
            "First-Sight": ("[ENGINE SPECIFIC: FIRST-SIGHT]", "accelerated_proximity is 4/5"),
            "Roommate-Romance": ("[ENGINE SPECIFIC: ROOMMATE-ROMANCE]", "boundary_play_heat is 2/5"),
            "Love-Neighbor": ("[ENGINE SPECIFIC: LOVE-NEIGHBOR]", "intersection_frequency is 3/5"),
        }

        for engine_type, (marker, detail) in expectations.items():
            with self.subTest(engine_type=engine_type):
                prompt = self.mapper.compile_system_prompt(self.make_payload(engine_type))
                self.assertIn(marker, prompt)
                self.assertIn(detail, prompt)

    def test_compile_system_prompt_renders_expanded_engine_variants(self) -> None:
        legacy_expectations = {
            "Meet-Cute": "platonic_trust is 4/5",
            "Meet-Ugly": "rivalry_heat is 4/5",
            "Meet-Crazy": "adrenaline_level is 5/5",
        }
        for engine_type, preset in NEW_ENGINE_STATE_PRESETS.items():
            if engine_type == "Fake-Dating":
                marker = "[TROPE ENGINE DIRECTIVE: THE FAKE-DATING MASK]"
                detail = "Boundary Panic [2/5]"
            elif engine_type in legacy_expectations:
                marker = f"[ENGINE SPECIFIC: {engine_type.upper()}]"
                detail = legacy_expectations[engine_type]
            else:
                marker = f"[ENGINE SPECIFIC: {engine_type.upper()}]"
                _focus_a, focus_b = preset["prompt_focus_keys"]
                detail = f"{focus_b} is {preset['weights'][focus_b]}/5"

            with self.subTest(engine_type=engine_type):
                prompt = self.mapper.compile_system_prompt(self.make_payload(engine_type))
                self.assertIn(marker, prompt)
                self.assertIn(detail, prompt)

    def test_fake_dating_prompt_sub_block_switches_private_behavior(self) -> None:
        block = compile_fake_dating_prompt_sub_block(
            {
                "performative_closeness": 4,
                "private_confusion": 3,
                "boundary_panic": 2,
                "lie_active": True,
            },
            "Inside a quiet, locked apartment living room after hours.",
        )

        self.assertIn("[ACTIVE LAYER: PRIVATE ISOLATION DETECTED]", block)
        self.assertIn("Boundary Panic rating is 2/5", block)
        self.assertIn("PRIDE PROTECTION ACTIVE", block)


if __name__ == "__main__":
    unittest.main()
